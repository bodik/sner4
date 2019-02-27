"""db commands"""

import click
from flask.cli import with_appcontext
from sner.server.extensions import db
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
		name='nmap ping host discovery',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200 -sn')
	db.session.add(task)
	db.session.commit()

	queue = Queue(name='ping localhost', task=task, group_size=5, priority=0, active=True)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target=target, queue=queue))
	db.session.commit()

	queue = Queue(name='ping localhost 1', task=task, group_size=1, priority=10, active=False)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target=target, queue=queue))
	db.session.commit()

	task = Task(
		name='nmap default SYN scan',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200 -sS')
	db.session.add(task)
	db.session.commit()
