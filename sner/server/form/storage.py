"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, StringField, TextAreaField, validators


class HostForm(FlaskForm):
	"""host edit form"""

	address = StringField('Address', validators=[validators.IPAddress(ipv4=True, ipv6=True)])
	hostname = StringField('Hostname', validators=[validators.Length(max=256)])
	os = StringField('Os')
