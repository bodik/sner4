from flask_wtf import FlaskForm
from wtforms import Field, StringField, validators
from wtforms.widgets import TextArea


class LinesField(Field):
	widget = TextArea()

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



class TaskForm(FlaskForm):
	name = StringField(label="Name", validators=[validators.Length(max=1024)])
	targets = LinesField(label="Targets", validators=[validators.Length(max=1024)], widget=TextArea())



class DeleteButtonForm(FlaskForm):
	pass
