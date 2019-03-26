"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import TextAreaField


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


class ButtonForm(FlaskForm):
	"""generic button form"""
	pass
