"""job controler"""

import base64
import binascii
import json
import os
from datetime import datetime
from http import HTTPStatus
from time import sleep
from uuid import uuid4

import jsonschema
from datatables import ColumnDT, DataTables
from flask import current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import func
from sqlalchemy_filters import apply_filters

import sner.agent.protocol
from sner.server import db
from sner.server.controller.scheduler import blueprint
from sner.server.form import ButtonForm
from sner.server.model.scheduler import Job, Queue, Target
from sner.server.sqlafilter import filter_parser


def job_output_filename(job_id):
    """helper, returns path to job datafile, would go to (doctrine)Repository if sqlalchemy had one"""

    return os.path.join(current_app.config['SNER_VAR'], 'scheduler', job_id)


def job_delete(job):
    """job delete; used by controller and respective command"""

    output_file = job_output_filename(job.id)
    if os.path.exists(output_file):
        os.remove(output_file)
    db.session.delete(job)
    db.session.commit()
    return 0


@blueprint.route('/job/list')
def job_list_route():
    """list jobs"""

    return render_template('scheduler/job/list.html')


@blueprint.route('/job/list.json', methods=['GET', 'POST'])
def job_list_json_route():
    """list jobs, data endpoint"""

    columns = [
        ColumnDT(Job.id, mData='id'),
        ColumnDT(Queue.id, mData='queue_id'),
        ColumnDT(Queue.name, mData='queue_name'),
        ColumnDT(Job.assignment, mData='assignment'),
        ColumnDT(Job.retval, mData='retval'),
        ColumnDT(Job.time_start, mData='time_start'),
        ColumnDT(Job.time_end, mData='time_end'),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Job).outerjoin(Queue)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    jobs = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(jobs)


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
            except SQLAlchemyError:  # pragma: no cover  ; unable to test
                db.session.rollback()
                sleep(0.01)

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
                'id': str(uuid4()),
                'module': queue.task.module,
                'params': queue.task.params,
                'targets': assigned_targets}
            job = Job(id=assignment['id'], assignment=json.dumps(assignment), queue=queue)
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
