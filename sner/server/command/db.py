"""db commands"""

import click
from flask.cli import with_appcontext
from sner.server.extensions import db
from sner.server.model.scheduler import Profile, Task


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

	profile = Profile(
		name='nmap ping host discovery',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200 -sn')
	db.session.add(profile)
	db.session.commit()

	targets = [str(x) for x in range(1000)]
	task = Task(name='ping localhost', profile=profile, targets=targets, group_size=5, priority=0)
	db.session.add(task)
	task = Task(name='ping localhost 1', profile=profile, targets=targets, group_size=1, priority=0)
	db.session.add(task)
	db.session.commit()

	profile = Profile(
		name='nmap default SYN scan',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200 -sS')
	db.session.add(profile)
	db.session.commit()
