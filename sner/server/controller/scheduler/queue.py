"""controller queue"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.controller import role_required
from sner.server.controller.scheduler import blueprint
from sner.server.form import ButtonForm
from sner.server.form.scheduler import QueueEnqueueForm, QueueForm
from sner.server.model.scheduler import Queue, Target, Task
from sner.server.sqlafilter import filter_parser


@blueprint.route('/queue/list', methods=['GET'])
@role_required('operator')
def queue_list_route():
    """list queues"""

    return render_template('scheduler/queue/list.html')


@blueprint.route('/queue/list.json', methods=['GET', 'POST'])
@role_required('operator')
def queue_list_json_route():
    """list queues, data endpoint"""

    columns = [
        ColumnDT(Queue.id, mData='id'),
        ColumnDT(Queue.name, mData='name'),
        ColumnDT(Task.id, mData='task_id'),
        ColumnDT(Task.name, mData='task_name'),
        ColumnDT(Queue.group_size, mData='group_size'),
        ColumnDT(Queue.priority, mData='priority'),
        ColumnDT(Queue.active, mData='active'),
        ColumnDT(func.count(func.distinct(Target.id)), mData='nr_targets', global_search=False),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Queue) \
        .outerjoin(Task, Queue.task_id == Task.id).outerjoin(Target, Queue.id == Target.queue_id) \
        .group_by(Queue.id, Task.id)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    queues = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(queues)


@blueprint.route('/queue/add', methods=['GET', 'POST'])
@blueprint.route('/queue/add/<task_id>', methods=['GET', 'POST'])
@role_required('operator')
def queue_add_route(task_id=None):
    """queue add"""

    form = QueueForm(task=Task.query.filter(Task.id == task_id).one_or_none())

    if form.validate_on_submit():
        queue = Queue()
        form.populate_obj(queue)
        db.session.add(queue)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/addedit.html', form=form, form_url=url_for('scheduler.queue_add_route'))


@blueprint.route('/queue/edit/<queue_id>', methods=['GET', 'POST'])
@role_required('operator')
def queue_edit_route(queue_id):
    """queue edit"""

    queue = Queue.query.get(queue_id)
    form = QueueForm(obj=queue)

    if form.validate_on_submit():
        form.populate_obj(queue)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/addedit.html', form=form, form_url=url_for('scheduler.queue_edit_route', queue_id=queue_id))


@blueprint.route('/queue/enqueue/<queue_id>', methods=['GET', 'POST'])
@role_required('operator')
def queue_enqueue_route(queue_id):
    """queue enqueue"""

    queue = Queue.query.get(queue_id)
    form = QueueEnqueueForm()

    if form.validate_on_submit():
        targets = []
        for target in form.data['targets']:
            targets.append({'target': target, 'queue_id': queue.id})
        db.session.bulk_insert_mappings(Target, targets)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('scheduler/queue/enqueue.html', form=form, form_url=url_for('scheduler.queue_enqueue_route', queue_id=queue_id))


@blueprint.route('/queue/flush/<queue_id>', methods=['GET', 'POST'])
@role_required('operator')
def queue_flush_route(queue_id):
    """queue flush"""

    queue = Queue.query.get(queue_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.query(Target).filter(Target.queue_id == queue.id).delete()
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template(
        'button-generic.html',
        form=form,
        form_url=url_for('scheduler.queue_flush_route', queue_id=queue_id),
        button_caption='Flush')


@blueprint.route('/queue/delete/<queue_id>', methods=['GET', 'POST'])
@role_required('operator')
def queue_delete_route(queue_id):
    """queue delete"""

    queue = Queue.query.get(queue_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(queue)
        db.session.commit()
        return redirect(url_for('scheduler.queue_list_route'))

    return render_template('button-delete.html', form=form, form_url=url_for('scheduler.queue_delete_route', queue_id=queue_id))
