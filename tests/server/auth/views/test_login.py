# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.views.login tests
"""

from base64 import b64decode, b64encode
from http import HTTPStatus

from fido2 import cbor
from flask import url_for

from sner.server.auth.core import TOTPImpl
from sner.server.auth.models import User
from sner.server.extensions import db, webauthn
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server import get_csrf_token
from tests.server.auth import webauthn_device_init


def test_login(client, test_user):
    """test login"""

    tmp_password = PWS().generate()
    tmp = User.query.get(test_user.id)
    tmp.password = tmp_password
    db.session.commit()

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    form['password'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Invalid credentials.\');")]')

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    form['password'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_logout(cl_user):
    """test logout"""

    response = cl_user.get(url_for('auth.logout_route'))
    assert response.status_code == HTTPStatus.FOUND
    response = response.follow()
    assert response.lxml.xpath('//a[text()="Login"]')


def test_unauthorized(client, test_user):
    """test for not logged in, redirect and final login"""

    tmp_password = PWS().generate()
    tmp = User.query.get(test_user.id)
    tmp.password = tmp_password
    db.session.commit()

    response = client.get(url_for('auth.profile_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert '/auth/login?next=' in response.headers['Location']

    form = response.follow().form
    form['username'] = test_user.username
    form['password'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.profile_route') in response.headers['Location']


def test_forbidden(cl_user):
    """access forbidden"""

    response = cl_user.get(url_for('auth.user_list_route'), status='*')
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_login_totp(client, test_user):
    """test login totp"""

    tmp_password = PWS().generate()
    tmp_secret = TOTPImpl.random_base32()
    tmp = User.query.get(test_user.id)
    tmp.password = tmp_password
    tmp.totp = tmp_secret
    db.session.commit()

    response = client.get(url_for('auth.login_totp_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.login_route') in response.headers['Location']

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    form['password'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    form = response.follow().form
    form['code'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid code"]')

    form = response.form
    form['code'] = TOTPImpl(tmp_secret).current_code()
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_login_webauthn(client, test_user):
    """test login by webauthn"""

    device = webauthn_device_init(test_user)

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = response.follow()
    # some javascript code muset be emulated
    pkcro = cbor.decode(b64decode(client.post(url_for('auth.login_webauthn_pkcro_route'), {'csrf_token': get_csrf_token(client)}).body))
    assertion = device.get(pkcro, 'https://%s' % webauthn.rp.id)
    assertion_data = {
        'credentialRawId': assertion['rawId'],
        'authenticatorData': assertion['response']['authenticatorData'],
        'clientDataJSON': assertion['response']['clientDataJSON'],
        'signature': assertion['response']['signature'],
        'userHandle': assertion['response']['userHandle']}
    form = response.form
    form['assertion'] = b64encode(cbor.encode(assertion_data))
    response = form.submit()
    # and back to standard test codeflow
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_profile_webauthn_pkcro_route_invalid_request(client):
    """test error handling in pkcro route"""

    response = client.post(url_for('auth.login_webauthn_pkcro_route'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_login_webauthn_invalid_assertion(client, test_wncred):
    """test login by webauthn; error hanling"""

    response = client.get(url_for('auth.login_webauthn_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.login_route') in response.headers['Location']

    form = client.get(url_for('auth.login_route')).form
    form['username'] = User.query.get(test_wncred.user_id).username
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = response.follow()
    form = response.form
    form['assertion'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Login error during Webauthn authentication.\');")]')
