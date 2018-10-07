import click
from flask.cli import with_appcontext
from sner4web.extensions import db


@click.command(name="initdb", help="creates database")
@with_appcontext
def initdb():
	db.create_all()
