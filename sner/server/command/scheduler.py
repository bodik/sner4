"""scheduler commands"""

import click
from netaddr import IPNetwork
from flask.cli import with_appcontext
from sner.server import db
from sner.server.model.scheduler import Queue, Target, Task
from sqlalchemy import func


@click.group(name='scheduler', help='sner.server scheduler management')
def scheduler_command():
	"""scheduler commands click group/container"""
	pass


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
@click.argument('task_id', type=int)
@click.option('--name')
@click.option('--group_size', type=int, default=5)
@click.option('--priority', type=int, default=10)
@click.option('--active', is_flag=True)
@with_appcontext
def queue_add(task_id, **kwargs):
	"""add new queue"""

	task = Task.query.filter(Task.id == task_id).one_or_none()
	if not task:
		raise RuntimeError('no such task')

	queue = Queue(name=kwargs["name"], task=task, group_size=kwargs["group_size"], priority=kwargs["priority"], active=kwargs["active"])
	db.session.add(queue)
	db.session.commit()


@scheduler_command.command(name='queue_enqueue', help='add targets to queue')
@click.argument('queue_id', type=int)
@click.argument('argtargets', nargs=-1)
@click.option('--file', type=click.File('r'))
def queue_enqueue(queue_id, argtargets, **kwargs):
	"""enqueue targets to queue"""

	queue = Queue.query.filter(Queue.id == queue_id).one_or_none()
	if not queue:
		raise RuntimeError('no such queue')
	argtargets = list(argtargets)
	if kwargs["file"]:
		argtargets += kwargs["file"].read().splitlines()

	targets = []
	for target in argtargets:
		targets.append({'target': target, 'queue_id': queue.id})
	db.session.bulk_insert_mappings(Target, targets)
	db.session.commit()


@scheduler_command.command(name='queue_flush', help='flush all targets from queue')
@click.argument('queue_id', type=int)
def queue_flush(queue_id):
	"""flush targets from queue"""

	queue = Queue.query.filter(Queue.id == queue_id).one_or_none()
	if not queue:
		raise RuntimeError('no such queue')
	db.session.query(Target).filter(Target.queue_id == queue.id).delete()
	db.session.commit()


@scheduler_command.command(name='queue_delete', help='queue task')
@click.argument('queue_id', type=int)
@with_appcontext
def queue_delete(queue_id):
	"""delete queue"""

	queue = Queue.query.filter(Queue.id == queue_id).one_or_none()
	if not queue:
		raise RuntimeError('no such queue')
	db.session.delete(queue)
	db.session.commit()


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
