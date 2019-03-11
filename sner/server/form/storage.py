"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, StringField, TextAreaField, validators


class HostForm(FlaskForm):
	"""host edit form"""

	address = StringField('Address', validators=[validators.IPAddress(ipv4=True, ipv6=True)])
	hostname = StringField('Hostname', validators=[validators.Length(max=256)])
	os = StringField('Os')


class ServiceForm(FlaskForm):
	"""service edit form"""

	host_id = HiddenField()
	proto = StringField('Proto', validators=[validators.Length(max=10)])
	port = IntegerField('Port', validators=[validators.NumberRange(min=0, max=65535)])
	state = StringField('State', validators=[validators.Length(max=100)])
	name = StringField('Name', validators=[validators.Length(max=100)])
	info = TextAreaField('Info')


class NoteForm(FlaskForm):
	"""note edit form"""

	host_id = HiddenField()
	ntype = StringField('nType', validators=[validators.Length(max=500)])
	data = TextAreaField('Data')
