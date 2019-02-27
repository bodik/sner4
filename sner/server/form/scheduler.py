"""flask forms"""

from flask_wtf import FlaskForm
from sner.server.form import LinesField
from sner.server.model.scheduler import Profile
from wtforms import IntegerField, StringField, TextAreaField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField


class ProfileForm(FlaskForm):
	"""profile edit form"""

	name = StringField(label='Name', validators=[validators.Length(max=1000)])
	module = StringField(label='Module', validators=[validators.Length(max=100)])
	params = TextAreaField(label='Parameters')


class TaskForm(FlaskForm):
	"""task edit form"""

	name = StringField(label='Name', validators=[validators.Length(max=1000)])
	profile = QuerySelectField(query_factory=lambda: Profile.query.all(), allow_blank=False) # pylint: disable=unnecessary-lambda
	targets = LinesField(label='Targets', validators=[validators.Length(max=1000)])
	group_size = IntegerField(label='Group size', default=1)
	priority = IntegerField(label='Priority', default=0)
