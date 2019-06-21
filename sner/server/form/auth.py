"""auth forms"""

from flask import current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectMultipleField, StringField, ValidationError, validators, widgets

from sner.server.password_supervisor import PasswordSupervisor as PWS


def strong_password(form, field):
    """validate password field"""

    username = form.username.data if hasattr(form, 'username') else current_user.username
    pwsr = PWS().check_strength(field.data, username)
    if not pwsr.is_strong:
        raise ValidationError(pwsr.message)


def passwords_match(form, field):  # pylint: disable=unused-argument
    """match passwords for change password"""

    if form.password1.data != form.password2.data:
        raise ValidationError('Passwords does not match.')


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class LoginForm(FlaskForm):
    """login form"""

    username = StringField(label='Username', validators=[validators.InputRequired()])
    password = PasswordField(label='Password', validators=[validators.InputRequired()])


class UserForm(FlaskForm):
    """user edit form"""

    username = StringField(label='Username', validators=[validators.Length(min=1, max=256)])
    password = PasswordField(label='Password', validators=[validators.optional(), strong_password])
    email = StringField(label='Email', validators=[validators.Length(max=256)])
    active = BooleanField(label='Active')
    roles = MultiCheckboxField(label='Roles')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.roles.choices = [(x, x) for x in current_app.config['SNER_AUTH_ROLES']]


class UserChangePasswordForm(FlaskForm):
    """user change password form"""

    password1 = PasswordField(label='Password', validators=[passwords_match, strong_password])
    password2 = PasswordField(label='Repeat password', validators=[passwords_match, strong_password])
