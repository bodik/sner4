"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import FieldList, IntegerField, SelectField, StringField, TextAreaField, ValidationError, validators

from sner.server.form import LinesField
from sner.server.model.storage import Host, Service, SeverityEnum


def host_id_exists(form, field): # pylint: disable=unused-argument
	"""validate submitted host_id"""

	if not Host.query.filter(Host.id == field.data).one_or_none():
		raise ValidationError('No such host')


def service_id_exists_and_belongs_to_host(form, field): # pylint: disable=unused-argument
	"""validate submitted service_id"""

	if field.data:
		if not Service.query.filter(Service.id == field.data).one_or_none():
			raise ValidationError('No such service')
		if not Service.query.filter(Service.id == field.data, Service.host_id == form.host_id.data).one_or_none():
			raise ValidationError('Service does not belong to the host')


def empty_to_none(data):
	"""cast empty value/string to none"""

	return data or None


class HostForm(FlaskForm):
	"""host edit form"""

	address = StringField('Address', validators=[validators.IPAddress(ipv4=True, ipv6=True)])
	hostname = StringField('Hostname', validators=[validators.Length(max=256)])
	os = StringField('Os')
	comment = TextAreaField('Comment')


class ServiceForm(FlaskForm):
	"""service edit form"""

	host_id = IntegerField('Host_id', validators=[host_id_exists])
	proto = StringField('Proto', validators=[validators.Length(min=1, max=10)], filters=[empty_to_none])
	port = IntegerField('Port', validators=[validators.NumberRange(min=0, max=65535)])
	state = StringField('State', validators=[validators.Length(max=100)])
	name = StringField('Name', validators=[validators.Length(max=100)])
	info = StringField('Info', validators=[validators.Length(max=2000)])
	comment = TextAreaField('Comment')


class VulnForm(FlaskForm):
	"""note edit form"""

	host_id = IntegerField('Host_id', validators=[host_id_exists])
	service_id = IntegerField('Service_id', validators=[validators.Optional(), service_id_exists_and_belongs_to_host])
	name = StringField('Name', validators=[validators.Length(min=1, max=500)])
	xtype = StringField('xType', validators=[validators.Length(max=500)])
	severity = SelectField('Severity', choices=SeverityEnum.choices(), coerce=SeverityEnum.coerce)
	descr = TextAreaField('Descr')
	data = TextAreaField('Data')
	refs = LinesField('Refs')
	tags = LinesField('Tags')
	comment = TextAreaField('Comment')


class NoteForm(FlaskForm):
	"""note edit form"""

	host_id = IntegerField('Host_id', validators=[host_id_exists])
	service_id = IntegerField('Service_id', validators=[validators.Optional(), service_id_exists_and_belongs_to_host])
	xtype = StringField('xType', validators=[validators.Length(max=500)])
	data = TextAreaField('Data')
	comment = TextAreaField('Comment')


class IdsForm(FlaskForm):
	"""ajax; generic multi-id form"""

	ids = FieldList(IntegerField(validators=[validators.DataRequired()]), min_entries=1)


class TagByIdForm(FlaskForm):
	"""ajax; tagmulti action"""

	ids = FieldList(IntegerField(validators=[validators.DataRequired()]), min_entries=1)
	tag = StringField(validators=[validators.DataRequired()])
