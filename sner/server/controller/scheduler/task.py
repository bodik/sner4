"""controller task"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.controller import role_required
from sner.server.controller.scheduler import blueprint
from sner.server.form import ButtonForm
from sner.server.form.scheduler import TaskForm
from sner.server.model.scheduler import Task
from sner.server.sqlafilter import filter_parser


@blueprint.route('/task/list')
@role_required('operator')
def task_list_route():
    """list tasks"""

    return render_template('scheduler/task/list.html')


@blueprint.route('/task/list.json', methods=['GET', 'POST'])
@role_required('operator')
def task_list_json_route():
    """list tasks, data endpoint"""

    columns = [
        ColumnDT(Task.id, mData='id'),
        ColumnDT(Task.name, mData='name'),
        ColumnDT(Task.module, mData='module'),
        ColumnDT(Task.params, mData='params'),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Task)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    tasks = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(tasks)


@blueprint.route('/task/add', methods=['GET', 'POST'])
@role_required('operator')
def task_add_route():
    """add task"""

    form = TaskForm()

    if form.validate_on_submit():
        task = Task()
        form.populate_obj(task)
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('scheduler.task_list_route'))

    return render_template('scheduler/task/addedit.html', form=form, form_url=url_for('scheduler.task_add_route'))


@blueprint.route('/task/edit/<task_id>', methods=['GET', 'POST'])
@role_required('operator')
def task_edit_route(task_id):
    """edit task"""

    task = Task.query.get(task_id)
    form = TaskForm(obj=task)

    if form.validate_on_submit():
        form.populate_obj(task)
        db.session.commit()
        return redirect(url_for('scheduler.task_list_route'))

    return render_template('scheduler/task/addedit.html', form=form, form_url=url_for('scheduler.task_edit_route', task_id=task_id))


@blueprint.route('/task/delete/<task_id>', methods=['GET', 'POST'])
@role_required('operator')
def task_delete_route(task_id):
    """delete task"""

    task = Task.query.get(task_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for('scheduler.task_list_route'))

    return render_template('button-delete.html', form=form, form_url=url_for('scheduler.task_delete_route', task_id=task_id))
