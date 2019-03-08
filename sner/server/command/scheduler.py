"""scheduler commands"""

import json
import os

import click
from flask.cli import with_appcontext
from netaddr import IPNetwork
from sqlalchemy import func

from sner.server import db
from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job, Queue, Target, Task


def taskbyx(taskid):
	"""get task by id or name"""
	if taskid.isnumeric():
		task = Task.query.filter(Task.id == int(taskid)).one_or_none()
	else:
		task = Task.query.filter(Task.name == taskid).one_or_none()
	return task


def queuebyx(queueid):
	"""get queue by id or name"""
	if queueid.isnumeric():
		queue = Queue.query.filter(Queue.id == int(queueid)).one_or_none()
	else:
		queue = Queue.query.filter(Queue.name == queueid).one_or_none()
	return queue


@click.group(name='scheduler', help='sner.server scheduler management')
def scheduler_command():
	"""scheduler commands click group/container"""
	pass



## misc commands

@scheduler_command.command(name='enumips', help='enumerate ip address range')
@click.argument('targets', nargs=-1)
@click.option('--file', type=click.File('r'))
def enumips(targets, **kwargs):
	"""enumerate ip address range"""

	targets = list(targets)
	if kwargs["file"]:
		targets += kwargs["file"].read().splitlines()
	for item in targets:
		for tmp in IPNetwork(item).iter_hosts():
			print(tmp)



## task commands

@scheduler_command.command(name='task_list', help='tasks listing')
@with_appcontext
def task_list():
	"""list tasks"""

	headers = ['id', 'name', 'module', 'params']
	fmt = '%-4s %-20s %-10s %s'
	print(fmt % tuple(headers))
	for task in Task.query.all():
		print(fmt % (task.id, task.name, task.module, json.dumps(task.params)))


@scheduler_command.command(name='task_add', help='add a new task')
@click.argument('module')
@click.option('--name')
@click.option('--params', default='')
@with_appcontext
def task_add(module, **kwargs):
	"""add new task"""

	task = Task(module=module, name=kwargs["name"], params=kwargs["params"])
	db.session.add(task)
	db.session.commit()


@scheduler_command.command(name='task_delete', help='delete task')
@click.argument('task_id')
@with_appcontext
def task_delete(task_id):
	"""delete task"""

	task = taskbyx(task_id)
	db.session.delete(task)
	db.session.commit()


## queue commands

@scheduler_command.command(name='queue_list', help='queues listing')
@with_appcontext
def queue_list():
	"""list queues"""

	count_targets = {}
	for queue_id, count in db.session.query(Target.queue_id, func.count(Target.id)).group_by(Target.queue_id).all():
		count_targets[queue_id] = count

	headers = ['id', 'name', 'task', 'targets']
	fmt = '%-4s %-20s %-40s %-8s'
	print(fmt % tuple(headers))
	for queue in Queue.query.all():
		print(fmt % (queue.id, queue.name, queue.task, count_targets.get(queue.id, 0)))


@scheduler_command.command(name='queue_add', help='add a new queue')
@click.argument('task_id')
@click.option('--name')
@click.option('--group_size', type=int, default=5)
@click.option('--priority', type=int, default=10)
@click.option('--active', is_flag=True)
@with_appcontext
def queue_add(task_id, **kwargs):
	"""add new queue"""

	task = taskbyx(task_id)
	queue = Queue(name=kwargs["name"], task=task, group_size=kwargs["group_size"], priority=kwargs["priority"], active=kwargs["active"])
	db.session.add(queue)
	db.session.commit()


@scheduler_command.command(name='queue_enqueue', help='add targets to queue')
@click.argument('queue_id')
@click.argument('argtargets', nargs=-1)
@click.option('--file', type=click.File('r'))
@with_appcontext
def queue_enqueue(queue_id, argtargets, **kwargs):
	"""enqueue targets to queue"""

	queue = queuebyx(queue_id)
	argtargets = list(argtargets)
	if kwargs["file"]:
		argtargets += kwargs["file"].read().splitlines()

	targets = []
	for target in argtargets:
		targets.append({'target': target, 'queue_id': queue.id})
	db.session.bulk_insert_mappings(Target, targets)
	db.session.commit()


@scheduler_command.command(name='queue_flush', help='flush all targets from queue')
@click.argument('queue_id')
@with_appcontext
def queue_flush(queue_id):
	"""flush targets from queue"""

	queue = queuebyx(queue_id)
	db.session.query(Target).filter(Target.queue_id == queue.id).delete()
	db.session.commit()


@scheduler_command.command(name='queue_delete', help='delete queue')
@click.argument('queue_id')
@with_appcontext
def queue_delete(queue_id):
	"""delete queue"""

	queue = queuebyx(queue_id)
	db.session.delete(queue)
	db.session.commit()



## job commands

@scheduler_command.command(name='job_list', help='jobs listing')
@with_appcontext
def job_list():
	"""list jobs"""

	def format_datetime(value, fmt="%Y-%m-%dT%H:%M:%S"): # pylint: disable=unused-variable
		"""Format a datetime"""
		if value is None:
			return None
		return value.strftime(fmt)

	headers = ['id', 'queue', 'assignment', 'retval', 'time_start', 'time_end']
	fmt = '%-36s %-20s %-25s %6s %-20s %-20s'
	print(fmt % tuple(headers))
	for job in Job.query.all():
		print(fmt % (
			job.id,
			json.dumps(job.queue.name if job.queue else ''),
			json.dumps(job.assignment[:17]+'...'),
			job.retval,
			format_datetime(job.time_start),
			format_datetime(job.time_end)))


@scheduler_command.command(name='job_delete', help='delete job')
@click.argument('job_id')
@with_appcontext
def job_delete(job_id):
	"""delete queue"""

	job = Job.query.filter(Job.id == job_id).one_or_none()
	output_file = job_output_filename(job_id)
	if os.path.exists(output_file):
		os.remove(output_file)
	db.session.delete(job)
	db.session.commit()
