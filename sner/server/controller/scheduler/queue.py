"""controller queue"""

from flask import redirect, render_template, url_for
from sner.server.controller.scheduler import blueprint
from sner.server.extensions import db
from sner.server.form import GenericButtonForm
from sner.server.form.scheduler import QueueEnqueueForm, QueueForm
from sner.server.model.scheduler import Queue, Target, Task
from sner.server.utils import wait_for_lock
from sqlalchemy import func


@blueprint.route('/queue/list', methods=['GET'])
def queue_list_route():
	"""list queues"""

	queues = Queue.query.all()
	count_targets = {}
	for queue_id, count in db.session.query(Target.queue_id, func.count(Target.id)).group_by(Target.queue_id).all():
		count_targets[queue_id] = count

	return render_template(
		'scheduler/queue/list.html',
		queues=queues,
		count_targets=count_targets,
		generic_button_form=GenericButtonForm())


@blueprint.route('/queue/add', methods=['GET', 'POST'])
@blueprint.route('/queue/add/<task_id>', methods=['GET', 'POST'])
def queue_add_route(task_id=None):
	"""queue add"""

	form = QueueForm(task=Task.query.filter(Task.id == task_id).one_or_none())

	if form.validate_on_submit():
		queue = Queue()
		#TODO: http parameter pollution vs framework mass-assign vulnerability
		form.populate_obj(queue)
		db.session.add(queue)
		db.session.commit()
		return redirect(url_for('scheduler.queue_list_route'))

	return render_template('scheduler/queue/addedit.html', form=form, form_url=url_for('scheduler.queue_add_route'))


@blueprint.route('/queue/edit/<queue_id>', methods=['GET', 'POST'])
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
def queue_enqueue_route(queue_id):
	"""queue enqueue"""

	queue = Queue.query.get(queue_id)
	form = QueueEnqueueForm()

	if form.validate_on_submit():
		targets = []
		for target in form.data["targets"]:
			targets.append({'target': target, 'queue_id': queue.id})
		db.session.bulk_insert_mappings(Target, targets)
		db.session.commit()
		return redirect(url_for('scheduler.queue_list_route'))

	return render_template('scheduler/queue/enqueue.html', form=form, form_url=url_for('scheduler.queue_enqueue_route', queue_id=queue_id))


@blueprint.route('/queue/flush/<queue_id>', methods=['GET', 'POST'])
def queue_flush_route(queue_id):
	"""queue flush"""

	queue = Queue.query.get(queue_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.query(Target).filter(Target.queue_id == queue.id).delete()
		db.session.commit()
		return redirect(url_for('scheduler.queue_list_route'))

	return render_template('button_generic.html', form=form, form_url=url_for('scheduler.queue_flush_route', queue_id=queue_id), button_caption='Flush')


@blueprint.route('/queue/delete/<queue_id>', methods=['GET', 'POST'])
def queue_delete_route(queue_id):
	"""queue delete"""

	queue = Queue.query.get(queue_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.delete(queue)
		db.session.commit()
		return redirect(url_for('scheduler.queue_list_route'))

	return render_template('button_delete.html', form=form, form_url=url_for('scheduler.queue_delete_route', queue_id=queue_id))
