# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api controller; only a stubs for binding routes implementations to application uri space
"""

import base64
import binascii
import json
import os
from datetime import datetime, timedelta
from http import HTTPStatus
from random import random
from time import sleep
from uuid import uuid4

import jsonschema
import yaml
from flask import Blueprint, current_app, jsonify, request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import func

import sner.agent.protocol
from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import ExclMatcher


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


def wait_for_lock(table_name):
    """wait for database lock. lock must be released by caller either by commit or rollback"""

    counter = 3
    while counter:
        counter -= 1
        try:
            db.session.execute(f'LOCK TABLE {table_name} NOWAIT')
            return True
        except SQLAlchemyError:
            db.session.rollback()
            if counter:
                sleep(random())

    current_app.logger.warning('failed to acquire table lock')
    return False


def select_queue(queue_name):
    """
    select queue
    """

    # Select active queue; by id or highest priority queue with targets.
    query = Queue.query.filter(Queue.active)
    if queue_name:
        queue = query.filter(Queue.name == queue_name).one_or_none()
    else:
        queue = query.filter(Queue.targets.any()).order_by(Queue.priority.desc(), func.random()).first()

    return queue


def assign_targets(queue):
    """
    select targets for job
    """

    # Pop targets until `group_size` of targets are selected or no targets left in queue.
    # Blacklisted/excluded targets are discarded from queue in the process.
    # Queue is popped for queue.group_size each time for performance reasons.
    assigned_targets = []
    blacklist = ExclMatcher()
    while True:
        targets = Target.query.filter(Target.queue == queue).order_by(func.random()).limit(queue.group_size).all()
        if not targets:
            break

        delete_targets = []
        for target in targets:
            delete_targets.append(target.id)
            if blacklist.match(target.target):
                continue
            assigned_targets.append(target.target)
            if len(assigned_targets) == queue.group_size:
                break
        Target.query.filter(Target.id.in_(delete_targets)).delete(synchronize_session=False)
        db.session.commit()
        db.session.expire_all()

        if len(assigned_targets) == queue.group_size:
            break

    return assigned_targets


@blueprint.route('/v1/scheduler/job/assign')
@role_required('agent', api=True)
def v1_scheduler_job_assign_route():
    """
    assign job for worker
    """

    nowork = jsonify({})

    if not wait_for_lock(Target.__tablename__):
        return nowork

    queue = select_queue(request.args.get('queue'))
    if not queue:
        # release lock and return response-nowork
        db.session.commit()
        return nowork

    assigned_targets = assign_targets(queue)
    if not assigned_targets:
        # release lock and return response-nowork
        db.session.commit()
        return nowork

    assignment = {
        'id': str(uuid4()),
        'config': {} if queue.config is None else yaml.safe_load(queue.config),
        'targets': assigned_targets
    }
    job = Job(id=assignment['id'], assignment=json.dumps(assignment), queue=queue)
    db.session.add(job)
    db.session.commit()
    return jsonify(assignment)


@blueprint.route('/v1/scheduler/job/output', methods=['POST'])
@role_required('agent', api=True)
def v1_scheduler_job_output_route():
    """receive output from assigned job"""

    try:
        jsonschema.validate(request.json, schema=sner.agent.protocol.output)
        job_id = request.json['id']
        retval = request.json['retval']
        output = base64.b64decode(request.json['output'])
    except (jsonschema.exceptions.ValidationError, binascii.Error):
        return jsonify({'title': 'Invalid request'}), HTTPStatus.BAD_REQUEST

    job = Job.query.filter(Job.id == job_id).one_or_none()
    if job and (not job.retval):
        # requests for invalid, deleted, repeated or clashing job ids are discarded
        # agent should delete the output on it's side as well
        job.retval = retval
        os.makedirs(os.path.dirname(job.output_abspath), exist_ok=True)
        with open(job.output_abspath, 'wb') as ftmp:
            ftmp.write(output)
        job.time_end = datetime.utcnow()
        db.session.commit()

    return '', HTTPStatus.OK


@blueprint.route('/v1/stats/prometheus')
def v1_stats_prometheus_route():
    """returns internal stats; prometheus"""

    stats = {}

    stats['sner_storage_hosts_total'] = Host.query.count()
    stats['sner_storage_services_total'] = Service.query.count()
    stats['sner_storage_vulns_total'] = Vuln.query.count()
    stats['sner_storage_notes_total'] = Note.query.count()

    stale_horizont = datetime.utcnow() - timedelta(days=5)
    stats[f'sner_scheduler_jobs_total{{state="running"}}'] = Job.query.filter(Job.retval == None, Job.time_start > stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats[f'sner_scheduler_jobs_total{{state="stale"}}'] = Job.query.filter(Job.retval == None, Job.time_start < stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats[f'sner_scheduler_jobs_total{{state="finished"}}'] = Job.query.filter(Job.retval == 0).count()
    stats[f'sner_scheduler_jobs_total{{state="failed"}}'] = Job.query.filter(Job.retval != 0).count()

    queue_targets = db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    for queue, targets in queue_targets:
        stats[f'sner_scheduler_queue_targets_total{{name="{queue}"}}'] = targets

    output = '\n'.join(f'{key} {val}' for key, val in stats.items())
    return Response(output, mimetype='text/plain')
