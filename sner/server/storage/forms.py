# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
flask forms
"""

from flask_wtf import FlaskForm
from wtforms import FieldList, HiddenField, IntegerField, SelectField, SubmitField, ValidationError
from wtforms.validators import AnyOf, InputRequired, IPAddress, Length, NumberRange, Optional

from sner.server.forms import StringNoneField, TextAreaListField, TextAreaNoneField
from sner.server.storage.models import Host, Service, SeverityEnum


def host_id_exists(form, field):  # pylint: disable=unused-argument
    """validate submitted host_id"""

    if not Host.query.filter(Host.id == field.data).one_or_none():
        raise ValidationError('No such host')


def service_id_exists_and_belongs_to_host(form, field):  # pylint: disable=unused-argument
    """validate submitted service_id"""

    if field.data:
        if not Service.query.filter(Service.id == field.data).one_or_none():
            raise ValidationError('No such service')
        if not Service.query.filter(Service.id == field.data, Service.host_id == form.host_id.data).one_or_none():
            raise ValidationError('Service does not belong to the host')


class HostForm(FlaskForm):
    """host edit form"""

    address = StringNoneField('Address', [InputRequired(), IPAddress(ipv4=True, ipv6=True)])
    hostname = StringNoneField('Hostname', [Length(max=256)])
    os = StringNoneField('Os')
    tags = TextAreaListField('Tags', render_kw={'class': 'form-control tageditor'})
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')
    return_url = HiddenField()


class ServiceForm(FlaskForm):
    """service edit form"""

    host_id = IntegerField('Host_id', [InputRequired(), host_id_exists])
    proto = StringNoneField('Proto', [InputRequired(), Length(min=1, max=250)])
    port = IntegerField('Port', [InputRequired(), NumberRange(min=0, max=65535)])
    state = StringNoneField('State', [Length(max=250)])
    name = StringNoneField('Name', [Length(max=250)])
    info = StringNoneField('Info')
    tags = TextAreaListField('Tags', render_kw={'class': 'form-control tageditor'})
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')
    return_url = HiddenField()


class VulnForm(FlaskForm):
    """note edit form"""

    host_id = IntegerField('Host_id', [InputRequired(), host_id_exists])
    service_id = IntegerField('Service_id', [Optional(), service_id_exists_and_belongs_to_host])
    name = StringNoneField('Name', [InputRequired(), Length(min=1, max=1000)])
    xtype = StringNoneField('xType', [Length(max=250)])
    severity = SelectField('Severity', [InputRequired()], choices=SeverityEnum.choices(), coerce=SeverityEnum.coerce)
    descr = TextAreaNoneField('Descr', render_kw={'rows': '5'})
    data = TextAreaNoneField('Data', render_kw={'rows': '5'})
    refs = TextAreaListField('Refs', render_kw={'rows': '5'})
    tags = TextAreaListField('Tags', render_kw={'class': 'form-control tageditor'})
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')
    return_url = HiddenField()


class NoteForm(FlaskForm):
    """note edit form"""

    host_id = IntegerField('Host_id', [InputRequired(), host_id_exists])
    service_id = IntegerField('Service_id', [Optional(), service_id_exists_and_belongs_to_host])
    xtype = StringNoneField('xType', [Length(max=250)])
    data = TextAreaNoneField('Data', render_kw={'rows': '10'})
    tags = TextAreaListField('Tags', render_kw={'class': 'form-control tageditor'})
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')
    return_url = HiddenField()


class MultiidForm(FlaskForm):
    """ajax; generic multi-id form"""

    ids = FieldList(IntegerField('id', [InputRequired()]), min_entries=1)


class TagMultiidForm(FlaskForm):
    """ajax; tagmulti action"""

    ids = FieldList(IntegerField('id', [InputRequired()]), min_entries=1)
    tag = StringNoneField('tag', [InputRequired()])
    action = StringNoneField('action', [InputRequired(), AnyOf(['set', 'unset'])])


class AnnotateForm(FlaskForm):
    """generic annotation form; update tags and comments"""

    tags = TextAreaListField('Tags', render_kw={'class': 'form-control tageditor'})
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')
