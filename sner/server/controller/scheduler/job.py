"""job controler"""

import json
import uuid
from flask import jsonify, redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.model.scheduler import Job, ScheduledTarget, Task
from sner.server.utils import wait_for_lock
from sqlalchemy.sql.expression import func


@blueprint.route('/job/list')
def job_list_route():
	"""list jobs"""

	jobs = Job.query.all()
	return render_template('scheduler/job/list.html', jobs=jobs, generic_button_form=GenericButtonForm())


#TODO: post? csfr protection?
@blueprint.route('/job/assign')
@blueprint.route('/job/assign/<task_id>')
def job_assign_route(task_id=None):
	"""assign job for worker"""

	assignment = {}
	targets = []
	wait_for_lock(ScheduledTarget.__tablename__)

	task = Task.query.filter(Task.scheduled_targets.any())
	if task_id:
		task = task.filter(Task.id == task_id)
	task = task.order_by(Task.priority.desc()).first()

	if task:
		scheduled_targets = ScheduledTarget.query.filter(ScheduledTarget.task == task).order_by(func.random()).limit(task.group_size).all()
		if scheduled_targets:
			for item in scheduled_targets:
				targets.append(item.target)
				db.session.delete(item)

			assignment = {
				"id": str(uuid.uuid4()),
				"module": task.profile.module,
				"params": task.profile.params,
				"targets": targets}
			job = Job(id=assignment["id"], assignment=json.dumps(assignment), task=task, targets=targets)
			db.session.add(job)

	# at least, we have to clear the lock
	db.session.commit()
	return jsonify(assignment)


@blueprint.route('/job/delete/<job_id>', methods=['GET', 'POST'])
def job_delete_route(job_id):
	"""delete job"""

	job = Job.query.get(job_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.delete(job)
		db.session.commit()
		return redirect(url_for('scheduler.job_list_route'))

	return render_template('button_delete.html', form=form, form_url=url_for('scheduler.job_delete_route', job_id=job_id))
