"""flask forms"""

from flask_wtf import FlaskForm
from sner_web.models import Profile
from wtforms import IntegerField, StringField, TextAreaField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField


class LinesField(TextAreaField):
	"""textarea transparently handlink list of items"""

	# value to form
	def _value(self):
		if self.data:
			return '\n'.join(self.data)
		return ""

	# value from form
	def process_formdata(self, valuelist):
		if valuelist:
			self.data = valuelist[0].splitlines() # pylint: disable=attribute-defined-outside-init
		else:
			self.data = [] # pylint: disable=attribute-defined-outside-init


class GenericButtonForm(FlaskForm):
	"""generic button form"""
	pass


class ProfileForm(FlaskForm):
	"""profile edit form"""

	name = StringField(label='Name', validators=[validators.Length(max=1024)])
	arguments = TextAreaField(label='Arguments')


class TaskForm(FlaskForm):
	"""task edit form"""

	name = StringField(label='Name', validators=[validators.Length(max=1024)])
	priority = IntegerField(label='Priority', default=0)
	profile = QuerySelectField(query_factory=lambda: Profile.query.all(), allow_blank=False) # pylint: disable=unnecessary-lambda
	targets = LinesField(label='Targets', validators=[validators.Length(max=1024)])
