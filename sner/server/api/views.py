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
from time import sleep
from uuid import uuid4

import jsonschema
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import func

import sner.agent.protocol
from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.utils import ExclMatcher


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/v1/scheduler/job/assign')
@blueprint.route('/v1/scheduler/job/assign/<queue_ident>')
@role_required('agent', api=True)
def v1_scheduler_job_assign_route(queue_ident=None):
    """assign job for worker"""

    def wait_for_lock(table):
        """wait for database lock"""
        while True:
            try:
                db.session.execute('LOCK TABLE %s' % table)
                break
            except SQLAlchemyError:  # pragma: no cover  ; unable to test
                db.session.rollback()
                sleep(0.01)

    wait_for_lock(Target.__tablename__)

    # select active queue; by id or highest priority queue with targets
    query = Queue.query.filter(Queue.active)
    if queue_ident:
        if queue_ident.isnumeric():
            queue = query.filter(Queue.id == int(queue_ident)).one_or_none()
        else:
            queue = query.filter(Queue.ident == queue_ident).order_by(Queue.priority.desc()).first()
    else:
        queue = query.filter(Queue.targets.any()).order_by(Queue.priority.desc()).first()

    if not queue:
        # release lock and return response-nowork
        db.session.commit()
        return jsonify({})

    # draw until group_size number of targets are selected or no targets left in queue
    # blacklisted/excluded targets are discarded from queue in the process
    # queue is drawed for queue.group_size each time for performance reasons
    assigned_targets = []
    blacklist = ExclMatcher()
    while True:
        targets = Target.query.filter(Target.queue == queue).order_by(func.random()).limit(queue.task.group_size).all()
        if not targets:
            break

        for target in targets:
            db.session.delete(target)
            if blacklist.match(target.target):
                continue
            assigned_targets.append(target.target)
            if len(assigned_targets) == queue.task.group_size:
                break

        if len(assigned_targets) == queue.task.group_size:
            break

    if not assigned_targets:
        # all targets might got blacklisted, release lock and return response-nowork
        db.session.commit()
        return jsonify({})

    assignment = {
        'id': str(uuid4()),
        'module': queue.task.module,
        'params': '' if queue.task.params is None else queue.task.params,
        'targets': assigned_targets}
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
        # requests for invalid, deleted, repeated or clashing job ids are discarded, agent should delete the output on it's side as well
        job.retval = retval
        os.makedirs(os.path.dirname(job.output_abspath), exist_ok=True)
        with open(job.output_abspath, 'wb') as ftmp:
            ftmp.write(output)
        job.time_end = datetime.utcnow()
        db.session.commit()

    return '', HTTPStatus.OK
