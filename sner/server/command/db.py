"""db commands"""

import click
from flask.cli import with_appcontext
from sner.server import db
from sner.server.model.scheduler import Queue, Task, Target


@click.group(name='db', help='sner.server db management')
def db_command():
	"""db command group/container"""
	pass


@db_command.command(name='init', help='initialize database schema')
@with_appcontext
def db_init():
	"""initialize database schema"""

	db.create_all()


@db_command.command(name='initdata', help='put initial data to database')
@with_appcontext
def db_initdata():
	"""put initial data to database"""

	task = Task(
		name='dummy',
		module='dummy',
		params='--dummyparam 1')
	db.session.add(task)
	db.session.commit()

	queue = Queue(name='dummy', task=task, group_size=3, priority=10, active=True)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target=target, queue=queue))
	db.session.commit()


	task = Task(
		name='tcp fullport scan',
		module='nmap',
		params='-sS -A -p1-65535 -Pn --reason --min-hostgroup 16 --max-retries 4  --min-rate 900 --max-rate 1500') # --data-length?
	db.session.add(task)
	db.session.commit()

	queue = Queue(name='netx fullport', task=task, group_size=16, priority=10, active=False)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target='10.0.0.%d'%target, queue=queue))
	db.session.commit()
