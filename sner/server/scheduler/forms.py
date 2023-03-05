# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
flask forms
"""

import yaml
from flask_wtf import FlaskForm
from schema import SchemaError
from wtforms import BooleanField, IntegerField, SubmitField, ValidationError
from wtforms.validators import InputRequired, Length, NumberRange

from sner.agent.modules import REGISTERED_MODULES
from sner.server.forms import StringNoneField, TextAreaListField, TextAreaNoneField


def valid_agent_config(_, field):
    """validate module config"""

    try:
        config = yaml.safe_load(field.data)
    except (yaml.YAMLError, AttributeError) as exc:
        raise ValidationError(f'Invalid YAML: {str(exc)}') from None

    if (not isinstance(config, dict)) or ('module' not in config) or (config['module'] not in REGISTERED_MODULES):
        raise ValidationError('Invalid module specified')

    try:
        REGISTERED_MODULES[config['module']].CONFIG_SCHEMA.validate(config)
    except SchemaError as exc:
        raise ValidationError(f'Invalid config: {str(exc)}') from None


class QueueForm(FlaskForm):
    """queue edit form"""

    name = StringNoneField('Name', [InputRequired(), Length(min=1, max=250)])
    config = TextAreaNoneField('Config', [valid_agent_config], render_kw={'rows': '10'})
    group_size = IntegerField('Group size', [InputRequired(), NumberRange(min=1)], default=1)
    priority = IntegerField('Priority', [InputRequired()], default=0)
    active = BooleanField('Active')
    reqs = TextAreaListField('Requirements', render_kw={'class': 'form-control tageditor'})
    submit = SubmitField('Save')


class QueueEnqueueForm(FlaskForm):
    """queue enqueue form"""

    targets = TextAreaListField('Targets', [InputRequired()], render_kw={'rows': '10'})
    submit = SubmitField('Enqueue')
