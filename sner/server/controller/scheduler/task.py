"""controller task"""

from flask import Blueprint, redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.form.scheduler import TaskForm
from sner.server.model.scheduler import Job, Profile, ScheduledTarget, Task
from sner.server.utils import wait_for_lock


@blueprint.route('/task/list')
def task_list_route():
	"""list tasks"""

	tasks = Task.query.all()
	return render_template('scheduler/task/list.html', tasks=tasks, generic_button_form=GenericButtonForm())


@blueprint.route('/task/add', methods=['GET', 'POST'])
@blueprint.route('/task/add/<profile_id>', methods=['GET', 'POST'])
def task_add_route(profile_id=None):
	"""add task"""

	form = TaskForm(profile=Profile.query.filter(Profile.id==profile_id).one_or_none())

	if form.validate_on_submit():
		task = Task()
		form.populate_obj(task)
		db.session.add(task)
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
		db.session.commit()
		return redirect(url_for('scheduler.task_list_route'))

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


@blueprint.route('/task/targets/<task_id>/<action>', methods=['GET', 'POST'])
def task_targets_route(task_id, action):
	"""schedule/unschedule task targets to queue"""

	task = Task.query.get(task_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		wait_for_lock(ScheduledTarget.__tablename__)

		if action == 'unschedule':
			for item in task.scheduled_targets:
				db.session.delete(item)

		if action == 'schedule':
			for item in task.scheduled_targets:
				db.session.delete(item)
			for item in task.targets:
				db.session.add(ScheduledTarget(target=item, task=task))

		db.session.commit()

		return redirect(url_for('scheduler.task_list_route'))

	return render_template('button_generic.html', form=form, form_url=url_for('scheduler.task_targets_route', task_id=task_id, action=action), button_caption=action.title())
