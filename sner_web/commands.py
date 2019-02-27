"""command line interface"""

import click
from flask.cli import with_appcontext
from sner_web.extensions import db



@click.command(name="sner_initdb", help="initialize database schema")
@with_appcontext
def initdb():
	"""initialize database schema"""

	db.create_all()
