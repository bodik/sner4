# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler queue views
"""

from http import HTTPStatus

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, literal_column

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.scheduler.core import QueueManager
from sner.server.scheduler.forms import QueueEnqueueForm, QueueForm
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.scheduler.views import blueprint
from sner.server.utils import filter_query


@blueprint.route('/queue/list', methods=['GET'])
@session_required('operator')
def queue_list_route():
    """list queues"""

    return render_template('scheduler/queue/list.html')


@blueprint.route('/queue/list.json', methods=['GET', 'POST'])
@session_required('operator')
def queue_list_json_route():
    """list queues, data endpoint"""

    query_nr_targets = db.session.query(Target.queue_id, func.count(Target.id).label('cnt')).group_by(Target.queue_id).subquery()
    query_nr_jobs = db.session.query(Job.queue_id, func.count(Job.id).label('cnt')).group_by(Job.queue_id).subquery()
    columns = [
        ColumnDT(Queue.id, mData='id'),
        ColumnDT(Queue.name, mData='name'),
        ColumnDT(Queue.config, mData='config'),
        ColumnDT(Queue.group_size, mData='group_size'),
        ColumnDT(Queue.priority, mData='priority'),
        ColumnDT(Queue.active, mData='active'),
        ColumnDT(Queue.reqs, mData='reqs'),
        ColumnDT(func.coalesce(query_nr_targets.c.cnt, 0), mData='nr_targets', global_search=False),
        ColumnDT(func.coalesce(query_nr_jobs.c.cnt, 0), mData='nr_jobs', global_search=False),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Queue) \
        .outerjoin(query_nr_targets, Queue.id == query_nr_targets.c.queue_id) \
        .outerjoin(query_nr_jobs, Queue.id == query_nr_jobs.c.queue_id)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    queues = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(queues)


@blueprint.route('/queue/add', methods=['GET', 'POST'])
@session_required('operator')
def queue_add_route():
    """queue add"""

    form = QueueForm()

    if form.validate_on_submit():
        queue = Queue()
        form.populate_obj(queue)
        db.session.add(queue)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/addedit.html', form=form)


@blueprint.route('/queue/edit/<queue_id>', methods=['GET', 'POST'])
@session_required('operator')
def queue_edit_route(queue_id):
    """queue edit"""

    queue = Queue.query.get(queue_id)
    form = QueueForm(obj=queue)

    if form.validate_on_submit():
        form.populate_obj(queue)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/addedit.html', form=form)


@blueprint.route('/queue/enqueue/<queue_id>', methods=['GET', 'POST'])
@session_required('operator')
def queue_enqueue_route(queue_id):
    """queue enqueue; put targets into queue"""

    form = QueueEnqueueForm()

    if form.validate_on_submit():
        QueueManager.enqueue(Queue.query.get(queue_id), form.data['targets'])
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/enqueue.html', form=form)


@blueprint.route('/queue/flush/<queue_id>', methods=['GET', 'POST'])
@session_required('operator')
def queue_flush_route(queue_id):
    """queue flush; flush all targets from queue"""

    form = ButtonForm()

    if form.validate_on_submit():
        QueueManager.flush(Queue.query.get(queue_id))
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('button-generic.html', form=form, button_caption='Flush')


@blueprint.route('/queue/prune/<queue_id>', methods=['GET', 'POST'])
@session_required('operator')
def queue_prune_route(queue_id):
    """queue prune; delete all queue jobs"""

    form = ButtonForm()

    if form.validate_on_submit():
        try:
            QueueManager.prune(Queue.query.get(queue_id))
            return redirect(url_for('scheduler.queue_list_route'))
        except RuntimeError as exc:
            return jsonify({'message': f'Failed: {exc}'}), HTTPStatus.INTERNAL_SERVER_ERROR

    return render_template('button-generic.html', form=form, button_caption='Prune')


@blueprint.route('/queue/delete/<queue_id>', methods=['GET', 'POST'])
@session_required('operator')
def queue_delete_route(queue_id):
    """queue delete"""

    form = ButtonForm()

    if form.validate_on_submit():
        try:
            QueueManager.delete(Queue.query.get(queue_id))
            return redirect(url_for('scheduler.queue_list_route'))
        except RuntimeError as exc:
            return jsonify({'message': f'Failed: {exc}'}), HTTPStatus.INTERNAL_SERVER_ERROR

    return render_template('button-delete.html', form=form)
