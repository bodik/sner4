"""flask forms"""

import re
from ipaddress import ip_network

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField, ValidationError, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from sner.server.form import LinesField
from sner.server.model.scheduler import ExclFamily, Task


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


class TaskForm(FlaskForm):
    """profile edit form"""

    name = StringField(label='Name', validators=[validators.Length(max=1000)])
    module = StringField(label='Module', validators=[validators.Length(min=1, max=100)])
    params = TextAreaField(label='Parameters', render_kw={'rows': '10'})
    submit = SubmitField('Save')


class QueueForm(FlaskForm):
    """queue edit form"""

    name = StringField(label='Name', validators=[validators.Length(max=1000)])
    task = QuerySelectField(query_factory=lambda: Task.query.all(), allow_blank=False)  # pylint: disable=unnecessary-lambda
    group_size = IntegerField(label='Group size', default=1)
    priority = IntegerField(label='Priority', default=0)
    active = BooleanField(label='Active')
    submit = SubmitField('Save')


class QueueEnqueueForm(FlaskForm):
    """queue enqueue form"""

    targets = LinesField(label='Targets', render_kw={'rows': '10'})
    submit = SubmitField('Enqueue')


class ExclForm(FlaskForm):
    """exclustion edit form"""

    family = SelectField('Family', choices=ExclFamily.choices(), coerce=ExclFamily.coerce, validators=[valid_excl_family])
    value = StringField(label='Value', validators=[validators.Length(min=1, max=1000), valid_excl_value])
    comment = TextAreaField('Comment')
    submit = SubmitField('Save')


class ExclImportForm(FlaskForm):
    """exclusions list import form"""

    data = TextAreaField(label='Data', render_kw={'rows': '10'}, validators=[validators.InputRequired()])
    replace = BooleanField(label='Replace')
    submit = SubmitField('Import')
