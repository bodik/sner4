# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
flask forms
"""

import re
from ipaddress import ip_network

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, SubmitField, ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import InputRequired, Length, NumberRange

from sner.server.forms import StringNoneField, TextAreaListField, TextAreaNoneField, Unique
from sner.server.scheduler.models import ExclFamily, Queue, Task


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


def valid_queue_ident(form, field):
    """validate queue.ident uniqueness"""

    if Queue.query.filter(Queue.task_id == form.task.data.id, Queue.name == field.data).one_or_none():
        raise ValidationError('Queue identifier must be unique.')


def tasks():
    """returns list of tasks for selectfiled"""
    return Task.query.all()


class TaskForm(FlaskForm):
    """profile edit form"""

    name = StringNoneField('Name', [InputRequired(), Length(min=1, max=250), Unique(Task.name)])
    module = StringNoneField('Module', [InputRequired(), Length(min=1, max=250)])
    params = TextAreaNoneField('Parameters', render_kw={'rows': '10'})
    group_size = IntegerField('Group size', [InputRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Save')


class QueueForm(FlaskForm):
    """queue edit form"""

    task = QuerySelectField('Task', [InputRequired()], query_factory=tasks, allow_blank=False, get_label='name')
    name = StringNoneField('Name', [InputRequired(), Length(min=1, max=250), valid_queue_ident])
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
