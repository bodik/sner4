"""job controler"""

import json
import uuid
from flask import jsonify, redirect, render_template, url_for
from sner.server import db, wait_for_lock
from sner.server.controller.scheduler import blueprint
from sner.server.form import GenericButtonForm
from sner.server.model.scheduler import Job, Queue, Target
from sqlalchemy.sql.expression import func


@blueprint.route('/job/list')
def job_list_route():
	"""list jobs"""

	jobs = Job.query.all()
	return render_template('scheduler/job/list.html', jobs=jobs, generic_button_form=GenericButtonForm())


#TODO: post? csfr protection?
@blueprint.route('/job/assign')
@blueprint.route('/job/assign/<queue_id>')
def job_assign_route(queue_id=None):
	"""assign job for worker"""

	assignment = {}
	wait_for_lock(Target.__tablename__)

	if queue_id:
		queue = Queue.query.filter(Queue.id == queue_id).one_or_none()
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
