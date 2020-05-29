# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
flask forms
"""

import re
from ipaddress import ip_network

import yaml
from flask_wtf import FlaskForm
from schema import SchemaError
from wtforms import BooleanField, IntegerField, SelectField, SubmitField, ValidationError
from wtforms.validators import InputRequired, Length, NumberRange

from sner.agent.modules import registered_modules
from sner.server.forms import StringNoneField, TextAreaListField, TextAreaNoneField
from sner.server.scheduler.models import ExclFamily


def valid_excl_family(form, field):  # pylint: disable=unused-argument
    """validate exclusion family"""

    if field.data not in ExclFamily.__members__.values():
        raise ValidationError('Invalid family')


def valid_excl_value(form, field):
    """validate exclusion value"""

    if form.family.data == ExclFamily.network:
        try:
            ip_network(field.data)
        except ValueError as e:
            raise ValidationError(str(e))
    elif form.family.data == ExclFamily.regex:
        try:
            re.compile(field.data)
        except re.error:
            raise ValidationError('Invalid regex')


def valid_agent_config(form, field):
    """validate module config"""

    try:
        config = yaml.safe_load(field.data)
    except (yaml.YAMLError, AttributeError) as e:
        raise ValidationError(f'Invalid YAML: {str(e)}')

    if ('module' not in config) or (config['module'] not in registered_modules):
        raise ValidationError('Invalid module specified')

    try:
        registered_modules[config['module']].CONFIG_SCHEMA.validate(config)
    except SchemaError as e:
        raise ValidationError(f'Invalid config: {str(e)}')


class QueueForm(FlaskForm):
    """queue edit form"""

    name = StringNoneField('Name', [InputRequired(), Length(min=1, max=250)])
    config = TextAreaNoneField('Config', [valid_agent_config], render_kw={'rows': '10'})
    group_size = IntegerField('Group size', [InputRequired(), NumberRange(min=1)], default=1)
    priority = IntegerField('Priority', [InputRequired()], default=0)
    active = BooleanField('Active')
    submit = SubmitField('Save')


class QueueEnqueueForm(FlaskForm):
    """queue enqueue form"""

    targets = TextAreaListField('Targets', [InputRequired()], render_kw={'rows': '10'})
    submit = SubmitField('Enqueue')


class ExclForm(FlaskForm):
    """exclustion edit form"""

    family = SelectField('Family', [InputRequired(), valid_excl_family], choices=ExclFamily.choices(), coerce=ExclFamily.coerce)
    value = StringNoneField('Value', [InputRequired(), Length(min=1), valid_excl_value])
    comment = TextAreaNoneField('Comment')
    submit = SubmitField('Save')


class ExclImportForm(FlaskForm):
    """exclusions list import form"""

    data = TextAreaNoneField('Data', [InputRequired()], render_kw={'rows': '10'})
    replace = BooleanField('Replace')
    submit = SubmitField('Import')
