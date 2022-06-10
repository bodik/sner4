# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.views.profile tests
"""

import json
from base64 import b64decode, b64encode
from http import HTTPStatus

from fido2 import cbor
from flask import url_for
from soft_webauthn import SoftWebauthnDevice

from sner.server.auth.core import TOTPImpl
from sner.server.auth.models import User, WebauthnCredential
from sner.server.extensions import db, webauthn
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server import get_csrf_token


def test_profile_route(cl_user):
    """user profile index test"""

    response = cl_user.get(url_for('auth.profile_route'))
    assert response.status_code == HTTPStatus.OK


def test_profile_changepassword_route(cl_user):
    """user profile change password"""

    cur_password = PWS.generate()
    new_password = PWS.generate()
    user = User.query.filter(User.username == 'pytest_user').one()
    user.password = PWS.hash(cur_password)
    db.session.commit()

    form = cl_user.get(url_for('auth.profile_changepassword_route')).forms['user_change_password_form']
    form['current_password'] = cur_password
    form['password1'] = 'AlongPassword1'
    form['password2'] = 'AlongPassword2'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Passwords does not match."]')

    form = cl_user.get(url_for('auth.profile_changepassword_route')).forms['user_change_password_form']
    form['current_password'] = cur_password
    form['password1'] = 'weak'
    form['password2'] = 'weak'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "Password too short.")]')

    form = cl_user.get(url_for('auth.profile_changepassword_route')).forms['user_change_password_form']
    form['current_password'] = '1'
    form['password1'] = new_password
    form['password2'] = new_password
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Invalid current password.\');")]')

    form = cl_user.get(url_for('auth.profile_changepassword_route')).forms['user_change_password_form']
    form['current_password'] = cur_password
    form['password1'] = new_password
    form['password2'] = new_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    user = User.query.filter(User.username == 'pytest_user').one()
    assert PWS.compare(PWS.hash(new_password, PWS.get_salt(user.password)), user.password)


def test_profile_totp_route_enable(cl_user):
    """user profile enable totp"""

    form = cl_user.get(url_for('auth.profile_totp_route')).forms['totp_code_form']
    form['code'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid code (enable)"]')

    response = cl_user.get(url_for('auth.profile_totp_route'))
    secret = cl_user.app.session_interface.open_session(cl_user.app, response.request)['totp_new_secret']
    form = response.forms['totp_code_form']
    form['code'] = TOTPImpl(secret).current_code()
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    user = User.query.filter(User.username == 'pytest_user').one()
    assert user.totp


def test_profile_totp_route_disable(cl_user):
    """user profile disable totp"""

    tmp_secret = TOTPImpl.random_base32()
    user = User.query.filter(User.username == 'pytest_user').one()
    user.totp = tmp_secret
    db.session.commit()

    form = cl_user.get(url_for('auth.profile_totp_route')).forms['totp_code_form']
    form['code'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid code (disable)"]')

    form = cl_user.get(url_for('auth.profile_totp_route')).forms['totp_code_form']
    form['code'] = TOTPImpl(tmp_secret).current_code()
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    user = User.query.filter(User.username == 'pytest_user').one()
    assert not user.totp


def test_profile_webauthn_list_json_route(cl_user, webauthn_credential_factory):
    """profile webauthn credentials json route test"""

    wncred = webauthn_credential_factory.create(user=User.query.filter(User.username == 'pytest_user').one())

    response = cl_user.post(url_for('auth.profile_webauthn_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': wncred.name})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == wncred.name


def test_profile_webauthn_register_route(cl_user):
    """register new credential for user"""

    device = SoftWebauthnDevice()

    response = cl_user.get(url_for('auth.profile_webauthn_register_route'))
    # some javascript code must be emulated
    pkcco = cbor.decode(b64decode(cl_user.post(url_for('auth.profile_webauthn_pkcco_route'), {'csrf_token': get_csrf_token(cl_user)}).body))
    attestation = device.create(pkcco, f'https://{webauthn.rp.id}')
    attestation_data = {
        'clientDataJSON': attestation['response']['clientDataJSON'],
        'attestationObject': attestation['response']['attestationObject']}
    form = response.forms['webauthn_register_form']
    form['attestation'] = b64encode(cbor.encode(attestation_data))
    # and back to standard test codeflow
    form['name'] = 'pytest token'
    response = form.submit()

    assert response.status_code == HTTPStatus.FOUND
    user = User.query.filter(User.username == 'pytest_user').one()
    assert user.webauthn_credentials


def test_profile_webauthn_pkcco_route_invalid_request(cl_user):
    """test error handling in pkcco route"""

    response = cl_user.post(url_for('auth.profile_webauthn_pkcco_route'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_profile_webauthn_register_route_invalid_attestation(cl_user):
    """register new credential for user; error handling"""

    form = cl_user.get(url_for('auth.profile_webauthn_register_route')).forms['webauthn_register_form']
    form['attestation'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Error during registration.\');")]')


def test_profile_webauthn_edit_route(cl_user, webauthn_credential_factory):
    """profile edit webauthn credentials route test"""

    wncred = webauthn_credential_factory.create(user=User.query.filter(User.username == 'pytest_user').one())

    form = cl_user.post(url_for('auth.profile_webauthn_edit_route', webauthn_id=wncred.id)).forms['webauthn_edit_form']
    form['name'] = f'{form["name"].value}  edited'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert wncred.name == form['name'].value


def test_profile_webauthn_delete_route(cl_user, webauthn_credential_factory):
    """profile delete webauthn credentials route test"""

    wncred = webauthn_credential_factory.create(user=User.query.filter(User.username == 'pytest_user').one())

    form = cl_user.get(url_for('auth.profile_webauthn_delete_route', webauthn_id=wncred.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not WebauthnCredential.query.get(wncred.id)


def test_profile_apikey_route(cl_user):
    """profile delete webauthn credentials route test"""

    user = User.query.filter(User.username == 'pytest_user').one()
    assert not user.apikey

    form = cl_user.get(url_for('auth.profile_apikey_route', action='generate')).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert user.apikey

    form = cl_user.get(url_for('auth.profile_apikey_route', action='revoke')).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert not user.apikey
