"""job controler"""

import json
import random
import uuid
from flask import jsonify, redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.model.scheduler import Job, Target, Task
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
	wait_for_lock(Target.__tablename__)

	if task_id:
		task = Task.query.filter(Task.id == task_id).one_or_none()
	else:
		# select highest priority active task with some targets
		#TODO: a little magic here which kind of join, if any, is used
		task = Task.query.filter(Task.active == True, Task.id == Target.task_id).order_by(Task.priority.desc()).first()

	if task:
		assigned_targets = []
		for target in Target.query.filter(Target.task == task).order_by(func.random()).limit(task.group_size):
			assigned_targets.append(target.target)
			db.session.delete(target)

		if assigned_targets:
			assignment = {
				"id": str(uuid.uuid4()),
				"module": task.profile.module,
				"params": task.profile.params,
				"targets": assigned_targets}
			job = Job(id=assignment["id"], assignment=json.dumps(assignment), task=task, targets=assigned_targets)
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
