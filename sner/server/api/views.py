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
from uuid import uuid4

import jsonschema
import yaml
from flask import Blueprint, current_app, jsonify, request, Response
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import cast, func

import sner.agent.protocol
from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.heatmap import Heatmap
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import ExclMatcher


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name

TIMEOUT_ASSIGN = 3
TIMEOUT_OUTPUT = 30


def wait_for_lock(table_name, timeout):
    """wait for database lock. lock must be released by caller either by commit or rollback"""

    try:
        db.session.execute(f'SET LOCAL lock_timeout={timeout*1000}; LOCK TABLE {table_name}')
        return True
    except SQLAlchemyError:
        db.session.rollback()

    current_app.logger.warning('failed to acquire table lock')
    return False


def iterate_queues(queue_name, client_caps):
    """
    select queue
        * queue must be active
        * queue must have any targets enqueued
        * client capabilities (caps) must conform queue requirements (reqs)
        * must suffice client requested parameters (name)
        * queue is selected with priority in respect, but at random on same prio levels
    """

    ccaps = cast(client_caps, postgresql.ARRAY(db.String))
    query = Queue.query.filter(Queue.active).filter(Queue.targets.any()).filter(Queue.reqs.contained_by(ccaps))
    if queue_name:
        query = query.filter(Queue.name == queue_name)
    for queue in query.order_by(Queue.priority.desc(), func.random()).all():
        yield queue


def assign_targets(queue):
    """
    try to select targets from queue respecting current heatmap discarding excluded targets in the process
    """

    heatmap = Heatmap()
    blacklist = ExclMatcher()
    assigned_targets = []
    delete_targets = []

    # bypassing ORM should provide iterator cursor yielding data on demand (instead of large buffering)
    for item in db.session.execute(
        'SELECT id, target, hashval FROM target WHERE queue_id = :queue_id ORDER BY rand',
        {'queue_id': queue.id},
        execution_options={'stream_results': True}
    ):
        iid, itarget, ihashval = item

        if blacklist.match(itarget):
            delete_targets.append(iid)
            continue

        if heatmap.is_hot(ihashval):
            continue

        assigned_targets.append(itarget)
        delete_targets.append(iid)
        heatmap.put(ihashval)

        if len(assigned_targets) == queue.group_size:
            break

    if delete_targets:
        Target.query.filter(Target.id.in_(delete_targets)).delete(synchronize_session=False)
    if assigned_targets:
        heatmap.save()

    return assigned_targets


@blueprint.route('/scheduler/job/assign')
@role_required('agent', api=True)
def scheduler_job_assign_route():
    """
    assign job for worker
    """

    assignment = {}  # nowork
    selected_queue = None
    assigned_targets = None

    if not wait_for_lock(Target.__tablename__, TIMEOUT_ASSIGN):
        return assignment

    for queue in iterate_queues(request.args.get('queue'), request.args.getlist('caps')):
        assigned_targets = assign_targets(queue)
        if assigned_targets:
            selected_queue = queue
            break

    if assigned_targets:
        assignment = {
            'id': str(uuid4()),
            'config': {} if selected_queue.config is None else yaml.safe_load(selected_queue.config),
            'targets': assigned_targets
        }
        job = Job(id=assignment['id'], assignment=json.dumps(assignment), queue=selected_queue)
        db.session.add(job)

    db.session.commit()  # releases lock
    return jsonify(assignment)


@blueprint.route('/scheduler/job/output', methods=['POST'])
@role_required('agent', api=True)
def scheduler_job_output_route():
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

        if not wait_for_lock(Target.__tablename__, TIMEOUT_OUTPUT):
            return jsonify({'title': 'Server busy'}), HTTPStatus.TOO_MANY_REQUESTS

        job.retval = retval
        os.makedirs(os.path.dirname(job.output_abspath), exist_ok=True)
        with open(job.output_abspath, 'wb') as ftmp:
            ftmp.write(output)
        job.time_end = datetime.utcnow()

        heatmap = Heatmap()
        for target in json.loads(job.assignment)['targets']:
            heatmap.pop(Heatmap.hashval(target))
        heatmap.save()

        db.session.commit()  # commit job record and release lock

    return '', HTTPStatus.OK


@blueprint.route('/stats/prometheus')
def stats_prometheus_route():
    """returns internal stats; prometheus"""

    stats = {}

    stats['sner_storage_hosts_total'] = Host.query.count()
    stats['sner_storage_services_total'] = Service.query.count()
    stats['sner_storage_vulns_total'] = Vuln.query.count()
    stats['sner_storage_notes_total'] = Note.query.count()

    stale_horizont = datetime.utcnow() - timedelta(days=5)
    stats['sner_scheduler_jobs_total{{state="running"}}'] = Job.query.filter(Job.retval == None, Job.time_start > stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{{state="stale"}}'] = Job.query.filter(Job.retval == None, Job.time_start < stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{{state="finished"}}'] = Job.query.filter(Job.retval == 0).count()
    stats['sner_scheduler_jobs_total{{state="failed"}}'] = Job.query.filter(Job.retval != 0).count()

    queue_targets = db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    for queue, targets in queue_targets:
        stats[f'sner_scheduler_queue_targets_total{{name="{queue}"}}'] = targets

    output = '\n'.join(f'{key} {val}' for key, val in stats.items())
    return Response(output, mimetype='text/plain')
