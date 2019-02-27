"""command line interface"""

import click
from flask.cli import with_appcontext
from sner_web.extensions import db
from sner_web.models import Profile, Task



@click.command(name="sner_init_db", help="initialize database schema")
@with_appcontext
def init_db():
	"""initialize database schema"""

	db.create_all()



@click.command(name="sner_init_data", help="put initial data to database")
@with_appcontext
def init_data():
	"""put initial data to database"""

	profile = Profile(name="nmap ping host discovery", arguments="--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200  -sn")
	db.session.add(profile)
	db.session.commit()

	task = Task(name="ping localhost", priority=0, profile=profile, targets=["localhost"])
	db.session.add(task)
	db.session.commit()


	profile = Profile(name="nmap default SYN scan", arguments="--min-hostgroup 16 --max-retries 4 --min-rate 100 --max-rate 200  -sS")
	db.session.add(profile)
	db.session.commit()

