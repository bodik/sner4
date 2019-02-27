from flask_wtf import FlaskForm
from sner_web.models import Profile
from wtforms import IntegerField, StringField, TextAreaField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.widgets import TextArea


class LinesField(TextAreaField):
	# value to form
	def _value(self):
		if self.data:
			return "\n".join(self.data)
		else:
			return ""

	# value from form
	def process_formdata(self, valuelist):
		if valuelist:
			self.data = valuelist[0].splitlines()
		else:
			self.data = []



class DeleteButtonForm(FlaskForm):
	pass



class ProfileForm(FlaskForm):
	name = StringField(label="Name", validators=[validators.Length(max=1024)])
	arguments = TextAreaField(label="Arguments")


class TaskForm(FlaskForm):
	name = StringField(label="Name", validators=[validators.Length(max=1024)])
	priority = IntegerField(label="Priority", default=0)
	profile = QuerySelectField(query_factory=lambda: Profile.query.all(), allow_blank=False)
	targets = LinesField(label="Targets", validators=[validators.Length(max=1024)])
