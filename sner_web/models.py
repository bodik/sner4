"""sqlalchemy """
# pylint: disable=too-few-public-methods,abstract-method

import json
from datetime import datetime
from sner_web.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator



# model item to put basic structures to db
class Json(TypeDecorator):
	"""json type, allow to store basic structures (namely list) to database"""

	impl = db.Text
	def process_bind_param(self, value, dialect):
		return json.dumps(value)
	def process_result_value(self, value, dialect):
		return json.loads(value)



class Profile(db.Model):
	"""holds settings/arguments for type of scan/scanner. eg. host discovery, fast portmap, version scan, ..."""

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1024))
	arguments = db.Column(db.Text())
	tasks = relationship("Task", back_populates="profile")
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

	def __str__(self):
		return "<Profile: %s>" % self.name



class Task(db.Model):
	"""profile assignment for specific targets"""

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1024))
	priority = db.Column(db.Integer(), nullable=False)
	targets = db.Column(Json(), nullable=False)
	profile_id = db.Column(db.Integer(), db.ForeignKey("profile.id"), nullable=False)
	profile = relationship("Profile", back_populates="tasks")
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

	def __repr__(self):
		return "<%s>" % self.name

	def __str__(self):
		return "<Task: %s>" % self.name
