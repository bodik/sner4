# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api controller; only a stubs for binding routes implementations to application uri space
"""

import base64
import binascii
import json
import os
from datetime import datetime
from http import HTTPStatus
from random import random
from time import sleep
from uuid import uuid4

import jsonschema
import yaml
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import func

import sner.agent.protocol
from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.models import Job, Queue, Target
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


def assign_targets(queue_name=None):
    """
    select queue and targets for job

    :param str queue_name: queue name, targets are selected from the queue if specified
    :return: tuple of queue and targets list or `None, None` if queue not found or to targets available
    :rtype: (scheduler.Queue, list)
    """

    # Select active queue; by id or highest priority queue with targets.
    query = Queue.query.filter(Queue.active)
    if queue_name:
        queue = query.filter(Queue.name == queue_name).one_or_none()
    else:
        queue = query.filter(Queue.targets.any()).order_by(Queue.priority.desc(), func.random()).first()

    if not queue:
        return None, None

    # Pop targets until `group_size` of targets are selected or no targets left in queue.
    # Blacklisted/excluded targets are discarded from queue in the process.
    # Queue is popped for queue.group_size each time for performance reasons.
    assigned_targets = []
    blacklist = ExclMatcher()
    while True:
        targets = Target.query.filter(Target.queue == queue).order_by(func.random()).limit(queue.group_size).all()
        if not targets:
            break

        for target in targets:
            db.session.delete(target)
            if blacklist.match(target.target):
                continue
            assigned_targets.append(target.target)
            if len(assigned_targets) == queue.group_size:
                break

        if len(assigned_targets) == queue.group_size:
            break

    return queue, assigned_targets


@blueprint.route('/v1/scheduler/job/assign')
@blueprint.route('/v1/scheduler/job/assign/<queue_name>')
@role_required('agent', api=True)
def v1_scheduler_job_assign_route(queue_name=None):
    """
    assign job for worker

    :param str queue_name: queue name
    :return: json encoded assignment or empty object
    :rtype: flask.Response
    """

    if not wait_for_lock(Target.__tablename__):
        # return response-nowork
        return jsonify({})

    queue, assigned_targets = assign_targets(queue_name)
    if not assigned_targets:
        # release lock and return response-nowork
        db.session.commit()
        return jsonify({})

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
