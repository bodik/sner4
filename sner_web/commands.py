"""comman line interface for sner"""

import click
from flask.cli import with_appcontext
from sner_web.extensions import db



@click.command(name="sner_initdb", help="creates database")
@with_appcontext
def initdb():
	"""initialized database with full model"""
	db.create_all()
