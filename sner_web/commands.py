"""command line interface"""

import click
from flask.cli import with_appcontext
from .extensions import db
from .models import Profile, Task


@click.command(name='sner_init_db', help='initialize database schema')
@with_appcontext
def init_db():
	"""initialize database schema"""

	db.create_all()


@click.command(name='sner_init_data', help='put initial data to database')
@with_appcontext
def init_data():
	"""put initial data to database"""

	profile = Profile(
		name='nmap ping host discovery',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200  -sn')
	db.session.add(profile)
	db.session.commit()

	targets = [str(x) for x in range(1000)]
	task = Task(name='ping localhost', priority=0, targets=targets, profile=profile)
	db.session.add(task)
	task = Task(name='ping localhost 1', priority=0, targets=targets, profile=profile)
	db.session.add(task)
	db.session.commit()


	profile = Profile(
		name='nmap default SYN scan',
		module='nmap',
		params='--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200  -sS')
	db.session.add(profile)
	db.session.commit()
