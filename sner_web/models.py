from datetime import datetime
import json
from sner_web.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator


# model item to put basic structures to db
class Json(TypeDecorator):
	impl = db.Text
	def process_bind_param(self, value, dialect):
		return json.dumps(value)
	def process_result_value(self, value, dialect):
		return json.loads(value)



class Profile(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1024))
	arguments = db.Column(db.Text())
	tasks = relationship("Task", back_populates="profile")
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)



class Task(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(1024))
	priority = db.Column(db.Integer(), nullable=False)
	profile_id = db.Column(db.Integer(), db.ForeignKey("profile.id"))
	profile = relationship("Profile", back_populates="tasks")
	targets = db.Column(Json(), nullable=False)
	created = db.Column(db.DateTime(), default=datetime.utcnow)
	modified = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
