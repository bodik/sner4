"""job controler"""

import base64
import binascii
import json
import os
import time
import uuid
from datetime import datetime
from http import HTTPStatus

import jsonschema
from flask import current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import func

import sner.agent.protocol
from sner.server import db
from sner.server.controller.scheduler import blueprint
from sner.server.form import ButtonForm
from sner.server.model.scheduler import Job, Queue, Target


def job_output_filename(job_id):
    """helper, returns path to job datafile, would go to (doctrine)Repository if sqlalchemy had one"""
    return os.path.join(current_app.config['SNER_VAR'], 'scheduler', job_id)


def job_delete(job):
    """job delete; used by controller and respoctive command"""

    output_file = job_output_filename(job.id)
    if os.path.exists(output_file):
        os.remove(output_file)
    db.session.delete(job)
    db.session.commit()
    return 0


@blueprint.route('/job/list')
def job_list_route():
    """list jobs"""

    jobs = Job.query.all()
    return render_template('scheduler/job/list.html', jobs=jobs, button_form=ButtonForm())


@blueprint.route('/job/assign')
@blueprint.route('/job/assign/<queue_id>')
def job_assign_route(queue_id=None):
    """assign job for worker"""

    def wait_for_lock(table):
        """wait for database lock"""
        while True:
            try:
                db.session.execute('LOCK TABLE %s' % table)
                break
            except SQLAlchemyError:
                db.session.rollback()
                time.sleep(0.01)

    assignment = {}
    wait_for_lock(Target.__tablename__)

    if queue_id:
        if queue_id.isnumeric():
            queue = Queue.query.filter(Queue.id == int(queue_id)).one_or_none()
        else:
            queue = Queue.query.filter(Queue.name == queue_id).one_or_none()
    else:
        # select highest priority active task with some targets
        queue = Queue.query.filter(Queue.active, Queue.targets.any()).order_by(Queue.priority.desc()).first()

    if queue:
        assigned_targets = []
        for target in Target.query.filter(Target.queue == queue).order_by(func.random()).limit(queue.group_size):
            assigned_targets.append(target.target)
            db.session.delete(target)

        if assigned_targets:
            assignment = {
                "id": str(uuid.uuid4()),
                "module": queue.task.module,
                "params": queue.task.params,
                "targets": assigned_targets}
            job = Job(id=assignment["id"], assignment=json.dumps(assignment), queue=queue)
            db.session.add(job)

    # at least, we have to clear the lock
    db.session.commit()
    return jsonify(assignment)


@blueprint.route('/job/output', methods=['POST'])
def job_output_route():
    """receive output from assigned job"""

    try:
        jsonschema.validate(request.json, schema=sner.agent.protocol.output)
        job_id = request.json['id']
        retval = request.json['retval']
        output = base64.b64decode(request.json['output'])
    except (jsonschema.exceptions.ValidationError, binascii.Error):
        return jsonify({'status': HTTPStatus.BAD_REQUEST, 'title': 'Invalid request'}), HTTPStatus.BAD_REQUEST

    job_filename = job_output_filename(job_id)
    os.makedirs(os.path.dirname(job_filename), exist_ok=True)
    with open(job_filename, 'wb') as ftmp:
        ftmp.write(output)

    job = Job.query.filter(Job.id == job_id).one_or_none()
    job.retval = retval
    job.time_end = datetime.utcnow()
    db.session.commit()

    return jsonify({'status': HTTPStatus.OK}), HTTPStatus.OK


@blueprint.route('/job/delete/<job_id>', methods=['GET', 'POST'])
def job_delete_route(job_id):
    """delete job"""

    job = Job.query.get(job_id)
    form = ButtonForm()

    if form.validate_on_submit():
        job_delete(job)
        return redirect(url_for('scheduler.job_list_route'))

    return render_template('button-delete.html', form=form, form_url=url_for('scheduler.job_delete_route', job_id=job_id))
