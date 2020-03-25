# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth profile views; user profile self-management
"""

import json
import string
from base64 import b64decode, b64encode
from http import HTTPStatus
from random import SystemRandom
from socket import getfqdn

from datatables import ColumnDT, DataTables
from fido2 import cbor
from fido2.client import ClientData
from fido2.ctap2 import AttestationObject
from flask import current_app, flash, redirect, render_template, request, Response, session, url_for
from flask_login import current_user
from sqlalchemy import literal_column

from sner.server.auth.core import role_required, TOTPImpl, webauthn_credentials
from sner.server.auth.forms import TotpCodeForm, UserChangePasswordForm, WebauthnRegisterForm, WebauthnEditForm
from sner.server.auth.models import User, WebauthnCredential
from sner.server.auth.views import blueprint
from sner.server.extensions import db, webauthn
from sner.server.forms import ButtonForm
from sner.server.password_supervisor import PasswordSupervisor as PWS
from sner.server.utils import SnerJSONEncoder


def random_string(length=32):
    """generates random string"""
    return ''.join([SystemRandom().choice(string.ascii_letters + string.digits) for i in range(length)])


@blueprint.route('/profile', methods=['GET', 'POST'])
@role_required('user')
def profile_route():
    """general user profile route"""

    user = User.query.filter(User.id == current_user.id).one()
    return render_template('auth/profile/index.html', user=user)


@blueprint.route('/profile/changepassword', methods=['GET', 'POST'])
@role_required('user')
def profile_changepassword_route():
    """user profile change password"""

    form = UserChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.filter(User.id == current_user.id).one()

        if not PWS.compare(PWS.hash(form.current_password.data, PWS.get_salt(user.password)), user.password):
            flash('Invalid current password.', 'error')
        else:
            user.password = form.password1.data
            db.session.commit()
            flash('Password changed.', 'info')
            return redirect(url_for('auth.profile_route'))

    return render_template('auth/profile/changepassword.html', form=form)


@blueprint.route('/profile/totp', methods=['GET', 'POST'])
@role_required('user')
def profile_totp_route():
    """user profile totp management route"""

    user = User.query.get(current_user.id)
    form = TotpCodeForm()
    if form.validate_on_submit():
        if not user.totp:
            # enable totp
            if TOTPImpl(session.get('totp_new_secret')).verify_code(form.code.data):
                user.totp = session['totp_new_secret']
                db.session.commit()
                session.pop('totp_new_secret', None)
                return redirect(url_for('auth.profile_route'))
            form.code.errors.append('Invalid code (enable)')

        else:
            # disable totp
            if TOTPImpl(user.totp).verify_code(form.code.data):
                user.totp = None
                db.session.commit()
                session.pop('totp_new_secret', None)
                return redirect(url_for('auth.profile_route'))
            form.code.errors.append('Invalid code (disable)')

    provisioning_url = None
    if not user.totp:
        if 'totp_new_secret' not in session:
            session['totp_new_secret'] = TOTPImpl.random_base32()
        provisioning_url = TOTPImpl(session.get('totp_new_secret')).get_provisioning_uri(
            user.username, current_app.config['SERVER_NAME'] or getfqdn())

    return render_template('auth/profile/totp.html', form=form, secret=session.get('totp_new_secret'), provisioning_url=provisioning_url)


# webauthn.guide
#
# registration
#
# 1. create credential
#   - client retrieves publickKeyCredentialCreationOptions (pkcco) from server; state/challenge must be preserved on the server side
#   - client/navigator calls authenticator with options to create credential
#   - authenticator will create new credential and return an atestation response (new credential's public key + metadata)
#
# 2. register credential
#   - attestation is packed; credential object is RO, ArrayBuffers must be casted to views (Uint8Array) before CBOR encoding
#   - packed attestation is sent to the server for registration
#   - server verifies the attestation and stores credential public key and association with the user
#
# authentication
#
# 1. create assertion
#   - client retrieves publicKeyCredentialRequestOption (pkcro) from server; state/challenge has to be preserved on the server side
#   - client/navigator calls authenticator with options to generate assertion
# 2. authenticate (using) assertion
#   - assertion is packed; credential is RO, ArrayBuffers must be casted to views (Uint8Array) before CBOR encoding
#   - packed assertion is sent to the server for authentication
#   - server validates the assertion (challenge, signature) against registered user credentials and performs logon process on success

@blueprint.route('/profile/webauthn/list.json', methods=['GET', 'POST'])
@role_required('user')
def profile_webauthn_list_json_route():
    """get registered credentials list for current user"""

    columns = [
        ColumnDT(WebauthnCredential.id, mData='id', search_method='none', global_search=False),
        ColumnDT(WebauthnCredential.registered, mData='registered'),
        ColumnDT(WebauthnCredential.name, mData='name'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(WebauthnCredential) \
        .filter(WebauthnCredential.user_id == current_user.id) \
        .order_by(WebauthnCredential.registered.asc())
    creds = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(creds, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/profile/webauthn/pkcco', methods=['POST'])
@role_required('user')
def profile_webauthn_pkcco_route():
    """get publicKeyCredentialCreationOptions"""

    form = ButtonForm()
    if form.validate_on_submit():
        user = User.query.get(current_user.id)
        user_handle = random_string()
        exclude_credentials = webauthn_credentials(user)
        pkcco, state = webauthn.register_begin(
            {'id': user_handle.encode('utf-8'), 'name': user.username, 'displayName': user.username},
            exclude_credentials)
        session['webauthn_register_user_handle'] = user_handle
        session['webauthn_register_state'] = state
        return Response(b64encode(cbor.encode(pkcco)).decode('utf-8'), mimetype='text/plain')

    return '', HTTPStatus.BAD_REQUEST


@blueprint.route('/profile/webauthn/register', methods=['GET', 'POST'])
@role_required('user')
def profile_webauthn_register_route():
    """register credential for current user"""

    user = User.query.get(current_user.id)
    form = WebauthnRegisterForm()
    if form.validate_on_submit():
        try:
            attestation = cbor.decode(b64decode(form.attestation.data))
            auth_data = webauthn.register_complete(
                session.pop('webauthn_register_state'),
                ClientData(attestation['clientDataJSON']),
                AttestationObject(attestation['attestationObject']))

            db.session.add(WebauthnCredential(
                user_id=user.id,
                user_handle=session.pop('webauthn_register_user_handle'),
                credential_data=cbor.encode(auth_data.credential_data.__dict__),
                name=form.name.data))
            db.session.commit()

            return redirect(url_for('auth.profile_route'))
        except (KeyError, ValueError) as e:
            current_app.logger.exception(e)
            flash('Error during registration.', 'error')

    return render_template('auth/profile/webauthn_register.html', form=form)


@blueprint.route('/profile/webauthn/edit/<webauthn_id>', methods=['GET', 'POST'])
@role_required('user')
def profile_webauthn_edit_route(webauthn_id):
    """edit registered credential"""

    cred = WebauthnCredential.query.filter(WebauthnCredential.user_id == current_user.id, WebauthnCredential.id == webauthn_id).one()
    form = WebauthnEditForm(obj=cred)
    if form.validate_on_submit():
        form.populate_obj(cred)
        db.session.commit()
        return redirect(url_for('auth.profile_route'))

    return render_template('auth/profile/webauthn_edit.html', form=form)


@blueprint.route('/profile/webauthn/delete/<webauthn_id>', methods=['GET', 'POST'])
@role_required('user')
def profile_webauthn_delete_route(webauthn_id):
    """delete registered credential"""

    form = ButtonForm()
    if form.validate_on_submit():
        db.session.delete(
            WebauthnCredential.query.filter(WebauthnCredential.user_id == current_user.id, WebauthnCredential.id == webauthn_id).one())
        db.session.commit()
        return redirect(url_for('auth.profile_route'))

    return render_template('button-delete.html', form=form)
