"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, StringField, TextAreaField, ValidationError, validators

from sner.server.model.storage import Host


def host_id_exists(form, field):
	if not Host.query.filter(Host.id == field.data).one_or_none():
		raise ValidationError('No such host')


class HostForm(FlaskForm):
	"""host edit form"""

	address = StringField('Address', validators=[validators.IPAddress(ipv4=True, ipv6=True)])
	hostname = StringField('Hostname', validators=[validators.Length(max=256)])
	os = StringField('Os')


class ServiceForm(FlaskForm):
	"""service edit form"""

	host_id = IntegerField('Host_id', validators=[host_id_exists])
	proto = StringField('Proto', validators=[validators.Length(max=10)])
	port = IntegerField('Port', validators=[validators.NumberRange(min=0, max=65535)])
	state = StringField('State', validators=[validators.Length(max=100)])
	name = StringField('Name', validators=[validators.Length(max=100)])
	info = TextAreaField('Info')



class NoteForm(FlaskForm):
	"""note edit form"""

	host_id = IntegerField('Host_id', validators=[host_id_exists])
	ntype = StringField('nType', validators=[validators.Length(max=500)])
	data = TextAreaField('Data')
