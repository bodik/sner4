"""sqlalchemy models"""
# pylint: disable=too-few-public-methods,abstract-method

from sqlalchemy.dialects import postgresql

from sner.server import db


class Host(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	address = db.Column(postgresql.INET, nullable=False)
	hostname = db.Column(db.String(256))
