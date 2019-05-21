"""flask forms"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, StringField, TextAreaField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from sner.server.form import LinesField
from sner.server.model.scheduler import Task


class TaskForm(FlaskForm):
    """profile edit form"""

    name = StringField(label='Name', validators=[validators.Length(max=1000)])
    module = StringField(label='Module', validators=[validators.Length(max=100)])
    params = TextAreaField(label='Parameters')


class QueueForm(FlaskForm):
    """queue edit form"""

    name = StringField(label='Name', validators=[validators.Length(max=1000)])
    task = QuerySelectField(query_factory=lambda: Task.query.all(), allow_blank=False)  # pylint: disable=unnecessary-lambda
    group_size = IntegerField(label='Group size', default=1)
    priority = IntegerField(label='Priority', default=0)
    active = BooleanField(label='Active')


class QueueEnqueueForm(FlaskForm):
    """queue enqueue form"""

    targets = LinesField(label='Targets')
