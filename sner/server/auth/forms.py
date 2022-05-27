# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth forms
"""

from ipaddress import ip_network

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, SelectMultipleField, SubmitField, ValidationError
from wtforms.validators import EqualTo, InputRequired, Length, Optional
from wtforms.widgets import CheckboxInput, ListWidget

from sner.server.forms import StringNoneField, TextAreaListField
from sner.server.password_supervisor import PasswordSupervisor as PWS


def strong_password(_, field):
    """validate password field"""

    pwsr = PWS.check_strength(field.data)
    if not pwsr.is_strong:
        raise ValidationError(pwsr.message)


def valid_api_networks(_, field):
    """validate api_networks list config"""

    try:
        for item in field.data:
            ip_network(item)
    except ValueError as exc:
        raise ValidationError(f'Invalid value: {str(exc)}') from None


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class LoginForm(FlaskForm):
    """login form"""

    username = StringNoneField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Login')


class TotpCodeForm(FlaskForm):
    """totp code form"""

    code = StringNoneField('TOTP Code', [InputRequired()], render_kw={'autocomplete': 'off'})
    submit = SubmitField()


class UserForm(FlaskForm):
    """user edit form"""

    username = StringNoneField('Username', [InputRequired(), Length(min=1, max=250)])
    email = StringNoneField('Email', [Length(max=250)])
    active = BooleanField('Active')
    roles = MultiCheckboxField('Roles')
    new_password = PasswordField('Password', [Optional(), strong_password])
    api_networks = TextAreaListField('API Networks', [valid_api_networks], render_kw={'rows': '5'})
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.roles.choices = [(x, x) for x in current_app.config['SNER_AUTH_ROLES']]


class UserChangePasswordForm(FlaskForm):
    """user change password form"""

    current_password = PasswordField('Current password', [InputRequired()])
    password1 = PasswordField('New password', [InputRequired(), EqualTo('password2', 'Passwords does not match.'), strong_password])
    password2 = PasswordField('Repeat new password', [InputRequired()])
    submit = SubmitField('Change password')


class WebauthnLoginForm(FlaskForm):
    """webauthn login form"""

    assertion = HiddenField('Assertion', [InputRequired()])


class WebauthnRegisterForm(FlaskForm):
    """webauthn register token form"""

    attestation = HiddenField('Attestation', [InputRequired()])
    name = StringNoneField('Name', [Length(max=250)])
    submit = SubmitField('Register', render_kw={'disabled': True})


class WebauthnEditForm(FlaskForm):
    """webauthn edit token form"""

    name = StringNoneField('Name', [Length(max=250)])
    submit = SubmitField('Save')
