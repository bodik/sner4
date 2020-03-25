# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth login/authentication views
"""

from base64 import b64decode, b64encode
from http import HTTPStatus

from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AuthenticatorData
from flask import current_app, flash, redirect, request, render_template, Response, session, url_for
from flask_login import login_user, logout_user

from sner.server.auth.core import regenerate_session, redirect_after_login, TOTPImpl, webauthn_credentials
from sner.server.auth.forms import LoginForm, TotpCodeForm, WebauthnLoginForm
from sner.server.auth.models import User
from sner.server.auth.views import blueprint
from sner.server.extensions import login_manager, webauthn
from sner.server.forms import ButtonForm
from sner.server.password_supervisor import PasswordSupervisor as PWS


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

    return render_template('auth/login.html', form=form)


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

    return render_template('auth/login_totp.html', form=form)


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
