"""authentication handling module"""

import os
from base64 import b32decode, b32encode, b64decode, b64encode
from functools import wraps
from http import HTTPStatus
from time import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.twofactor import InvalidToken as InvalidTOTPToken
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AttestedCredentialData, AuthenticatorData
from flask import _request_ctx_stack, Blueprint, current_app, flash, g, redirect, request, render_template, Response, session, url_for
from flask_login import current_user, login_user, logout_user

from sner.server import login_manager, webauthn
from sner.server.form import ButtonForm
from sner.server.form.auth import LoginForm, TotpCodeForm, WebauthnLoginForm
from sner.server.model.auth import User
from sner.server.password_supervisor import PasswordSupervisor as PWS


blueprint = Blueprint('auth', __name__)  # pylint: disable=invalid-name


def regenerate_session():
    """regenerate session"""

    _request_ctx_stack.top.session = current_app.session_interface.new_session()
    if hasattr(g, 'csrf_token'):  # cleanup g, which is used by flask_wtf
        delattr(g, 'csrf_token')


def redirect_after_login():
    """handle next after successfull login"""

    if request.args.get('next'):
        for rule in current_app.url_map.iter_rules():
            if rule.rule.startswith(request.args.get('next')):
                return redirect(request.args.get('next'))
    return redirect(url_for('index_route'))


def role_required(role, api=False):
    """flask view decorator implementing role based authorization; does not redirect to login for api views/routes"""

    def _role_required(fnc):
        @wraps(fnc)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                if api:
                    return 'Unauthorized', HTTPStatus.UNAUTHORIZED
                return login_manager.unauthorized()

            if not current_user.has_role(role):
                return 'Forbidden', HTTPStatus.FORBIDDEN

            return fnc(*args, **kwargs)

        return decorated_view
    return _role_required


def webauthn_credentials(user):
    """get and decode all credentials for given user"""
    return [AttestedCredentialData.create(**cbor.decode(cred.credential_data)) for cred in user.webauthn_credentials]


class TOTPImpl(TOTP):
    """Custom class wrapping defaults for used TOTP impl (pyca/cryptography)"""

    def __init__(self, secret):
        """initialize totp
        :param secret: secret seed in base32 encoding
        """
        super().__init__(b32decode(secret), 6, SHA1(), 30, backend=default_backend())

    @staticmethod
    def random_base32():
        """generate new secret, return base32 encoded representation"""
        return b32encode(os.urandom(20)).decode('ascii')

    def current_code(self):
        """generate current code"""
        return super().generate(time())

    def verify_code(self, code):
        """verify code"""

        try:
            super().verify(code.encode('ascii'), time())
        except InvalidTOTPToken:
            return False
        return True


@login_manager.user_loader
def user_loader(user_id):
    """flask_login user loader"""

    return User.query.filter(User.id == user_id).one_or_none()


@login_manager.request_loader
def load_user_from_request(req):
    """api authentication; load user form request"""

    auth_header = req.headers.get('Authorization')
    if auth_header:
        apikey = auth_header.replace('Apikey ', '', 1)
        if apikey:
            return User.query.filter(User.active, User.apikey == PWS.hash_simple(apikey)).first()
    return None


@blueprint.route('/login', methods=['GET', 'POST'])
def login_route():
    """login route"""

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.active, User.username == form.username.data).one_or_none()
        if user:
            if form.password.data:
                if PWS.compare(PWS.hash(form.password.data, PWS.get_salt(user.password)), user.password):
                    if user.totp:
                        session['totp_login_user_id'] = user.id
                        return redirect(url_for('auth.login_totp_route', **request.args))

                    regenerate_session()
                    login_user(user)
                    return redirect_after_login()
            else:
                if user.webauthn_credentials:
                    session['webauthn_login_user_id'] = user.id
                    return redirect(url_for('auth.login_webauthn_route', **request.args))

        flash('Invalid credentials.', 'error')

    return render_template('auth/login.html', form=form, form_url=url_for('auth.login_route', **request.args))


@blueprint.route('/logout')
def logout_route():
    """logout route"""

    logout_user()
    session.clear()
    return redirect(url_for('index_route'))


@blueprint.route('/login_totp', methods=['GET', 'POST'])
def login_totp_route():
    """login totp route"""

    user = User.query.filter(User.active, User.id == session.get('totp_login_user_id')).one_or_none()
    if not user:
        return login_manager.unauthorized()

    form = TotpCodeForm()
    if form.validate_on_submit():
        if TOTPImpl(user.totp).verify_code(form.code.data):
            regenerate_session()
            login_user(user)
            return redirect_after_login()

        form.code.errors.append('Invalid code')

    return render_template('auth/login_totp.html', form=form, form_url=url_for('auth.login_totp_route', **request.args))


@blueprint.route('/login_webauthn_pkcro', methods=['POST'])
def login_webauthn_pkcro_route():
    """login webauthn pkcro route"""

    user = User.query.filter(User.id == session.get('webauthn_login_user_id')).one_or_none()
    form = ButtonForm()
    if user and form.validate_on_submit():
        pkcro, state = webauthn.authenticate_begin(webauthn_credentials(user))
        session['webauthn_login_state'] = state
        return Response(b64encode(cbor.encode(pkcro)).decode('utf-8'), mimetype='text/plain')

    return '', HTTPStatus.BAD_REQUEST


@blueprint.route('/login_webauthn', methods=['GET', 'POST'])
def login_webauthn_route():
    """login webauthn route"""

    user = User.query.filter(User.id == session.get('webauthn_login_user_id')).one_or_none()
    if not user:
        return login_manager.unauthorized()

    form = WebauthnLoginForm()
    if form.validate_on_submit():
        try:
            assertion = cbor.decode(b64decode(form.assertion.data))
            webauthn.authenticate_complete(
                session.pop('webauthn_login_state'),
                webauthn_credentials(user),
                assertion['credentialRawId'],
                ClientData(assertion['clientDataJSON']),
                AuthenticatorData(assertion['authenticatorData']),
                assertion['signature'])
            regenerate_session()
            login_user(user)
            return redirect_after_login()

        except (KeyError, ValueError) as e:
            current_app.logger.exception(e)
            flash('Login error during Webauthn authentication.', 'error')

    return render_template('auth/login_webauthn.html', form=form)


import sner.server.controller.auth.profile  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.auth.user  # noqa: E402,F401  pylint: disable=wrong-import-position
