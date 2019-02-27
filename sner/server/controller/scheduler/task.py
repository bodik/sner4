"""controller task"""

from flask import current_app, redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.form.scheduler import TaskForm
from sner.server.model.scheduler import Job, Profile, Target, Task
from sner.server.utils import wait_for_lock
from sqlalchemy import func


@blueprint.route('/task/list', methods=['GET'])
def task_list_route():
	"""list tasks"""

	tasks = Task.query.all()
	count_targets = {}
	for task_id, count in db.session.query(Target.task_id, func.count(Target.id)).group_by(Target.task_id).all():
		count_targets[task_id] = count

	return render_template(
		'scheduler/task/list.html',
		tasks=tasks,
		count_targets=count_targets,
		generic_button_form=GenericButtonForm())


@blueprint.route('/task/add', methods=['GET', 'POST'])
@blueprint.route('/task/add/<profile_id>', methods=['GET', 'POST'])
def task_add_route(profile_id=None):
	"""add task"""

	form = TaskForm(profile=Profile.query.filter(Profile.id == profile_id).one_or_none())

	if form.validate_on_submit():
		task = Task()
		#TODO: http parameter pollution vs framework mass-assign vulnerability
		form.populate_obj(task)
		db.session.add(task)
		for target in form.data["targets_field"]:
			db.session.add(Target(target=target, task=task))
		db.session.commit()
		return redirect(url_for('scheduler.task_list_route'))

	return render_template('scheduler/task/addedit.html', form=form, form_url=url_for('scheduler.task_add_route'))


@blueprint.route('/task/edit/<task_id>', methods=['GET', 'POST'])
def task_edit_route(task_id):
	"""edit task"""

	task = Task.query.get(task_id)
	form = TaskForm(obj=task)

	if form.validate_on_submit():
		form.populate_obj(task)
		#TODO: better targets update handling, full replacement would not work on just update of the priority in the middle of the task
		for target in Target.query.filter(Target.task == task).all():
			db.session.delete(target)
		for target in form.data["targets_field"]:
			db.session.add(Target(target=target, task=task))
		db.session.commit()
		return redirect(url_for('scheduler.task_list_route'))

	form.targets_field.data = [tmp.target for tmp in Target.query.filter(Target.task == task).all()]
	return render_template('scheduler/task/addedit.html', form=form, form_url=url_for('scheduler.task_edit_route', task_id=task_id))


@blueprint.route('/task/delete/<task_id>', methods=['GET', 'POST'])
def task_delete_route(task_id):
	"""delete task"""

	task = Task.query.get(task_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.delete(task)
		db.session.commit()
		return redirect(url_for('scheduler.task_list_route'))

	return render_template('button_delete.html', form=form, form_url=url_for('scheduler.task_delete_route', task_id=task_id))
