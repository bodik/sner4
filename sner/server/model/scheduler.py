"""sqlalchemy models"""
# pylint: disable=too-few-public-methods,abstract-method

# caveat: beware of db.JSON change tracking which works only on full
# assignment, not for list operations such as .pop(), .append() use
# sqlalchemy...flag_modified to ensure the change on commit(). alternatives
# such as NestedMutableJson has severe performance penatly for large (10^3
# items lists)

from datetime import datetime
from sqlalchemy.orm import relationship
from sner.server.extensions import db


class Profile(db.Model):
	"""holds settings/arguments for type of scan/scanner. eg. host discovery, fast portmap, version scan, ..."""

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1000))
	module = db.Column(db.String(100), nullable=False)
	params = db.Column(db.Text())
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

	tasks = relationship('Task', back_populates='profile')

	def __str__(self):
		return '<Profile: %s>' % self.name


class Task(db.Model):
	"""profile assignment for specific targets"""

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1000))
	profile_id = db.Column(db.Integer(), db.ForeignKey('profile.id'), nullable=False)
	group_size = db.Column(db.Integer(), nullable=False)
	priority = db.Column(db.Integer(), nullable=False)
	active = db.Column(db.Boolean())
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

	profile = relationship('Profile', back_populates='tasks')
	targets = relationship('Target', back_populates='task', cascade='delete,delete-orphan')
	jobs = relationship('Job', back_populates='task', cascade='delete,delete-orphan')

	def __repr__(self):
		return '<Task: %s>' % self.name
	def __str__(self):
		return '<Task: %s>' % self.name


class Target(db.Model):
	"""single target of the task"""

	id = db.Column(db.Integer, primary_key=True)
	target = db.Column(db.Text())
	task_id = db.Column(db.Integer(), db.ForeignKey('task.id'), nullable=False)

	task = relationship('Task', back_populates='targets')


class Job(db.Model):
	"""assigned job"""

	id = db.Column(db.String(100), primary_key=True)
	assignment = db.Column(db.Text())
	result = db.Column(db.LargeBinary)
	task_id = db.Column(db.Integer(), db.ForeignKey('task.id'), nullable=False)
	targets = db.Column(db.JSON(), nullable=False)
	time_start = db.Column(db.DateTime(), default=datetime.utcnow)
	time_end = db.Column(db.DateTime())

	task = relationship('Task', back_populates='jobs')
