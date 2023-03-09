# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.views.login tests
"""

from base64 import b64decode, b64encode
from http import HTTPStatus
from unittest.mock import Mock, patch

from authlib.common.errors import AuthlibBaseError
from fido2 import cbor
from flask import current_app, redirect, url_for
from soft_webauthn import SoftWebauthnDevice

from sner.server.auth.core import TOTPImpl
from sner.server.extensions import oauth, webauthn
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server import get_csrf_token


def test_session_login(client, user_factory):
    """test login"""

    password = PWS.generate()
    user = user_factory.create(password=PWS.hash(password))

    form = client.get(url_for('auth.login_route')).forms['login_form']
    form['username'] = user.username
    form['password'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Invalid credentials.\');")]')

    form = client.get(url_for('auth.login_route')).forms['login_form']
    form['username'] = user.username
    form['password'] = password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_session_logout(cl_user):
    """test logout"""

    response = cl_user.get(url_for('auth.logout_route'))
    assert response.status_code == HTTPStatus.FOUND
    response = response.follow()
    assert response.lxml.xpath('//a[text()="Login"]')


def test_session_unauthorized(client, user_factory):
    """test for not logged in, redirect and final login"""

    password = PWS.generate()
    user = user_factory.create(password=PWS.hash(password))

    response = client.get(url_for('auth.profile_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert '/auth/login?next=' in response.headers['Location']

    form = response.follow().forms['login_form']
    form['username'] = user.username
    form['password'] = password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.profile_route') in response.headers['Location']


def test_session_forbidden(cl_user):
    """access forbidden"""

    response = cl_user.get(url_for('auth.user_list_route'), status='*')
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_login_totp(client, user_factory):
    """test login totp"""

    password = PWS.generate()
    secret = TOTPImpl.random_base32()
    user = user_factory(password=PWS.hash(password), totp=secret)

    response = client.get(url_for('auth.login_totp_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.login_route') in response.headers['Location']

    form = client.get(url_for('auth.login_route')).forms['login_form']
    form['username'] = user.username
    form['password'] = password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    form = response.follow().forms['totp_code_form']
    form['code'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid code"]')

    form = response.forms['totp_code_form']
    form['code'] = TOTPImpl(secret).current_code()
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_login_webauthn(client, webauthn_credential_factory):
    """test login by webauthn"""

    device = SoftWebauthnDevice()
    device.cred_init(webauthn.rp.id, b'randomhandle')
    wncred = webauthn_credential_factory.create(initialized_device=device)

    form = client.get(url_for('auth.login_route')).forms['login_form']
    form['username'] = wncred.user.username
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = response.follow()
    # some javascript code muset be emulated
    pkcro = cbor.decode(b64decode(client.post(url_for('auth.login_webauthn_pkcro_route'), {'csrf_token': get_csrf_token(client)}).body))
    assertion = device.get(pkcro, f'https://{webauthn.rp.id}')
    assertion_data = {
        'credentialRawId': assertion['rawId'],
        'authenticatorData': assertion['response']['authenticatorData'],
        'clientDataJSON': assertion['response']['clientDataJSON'],
        'signature': assertion['response']['signature'],
        'userHandle': assertion['response']['userHandle']}
    form = response.forms['webauthn_login_form']
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


def test_login_webauthn_invalid_assertion(client, webauthn_credential):
    """test login by webauthn; error hanling"""

    response = client.get(url_for('auth.login_webauthn_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.login_route') in response.headers['Location']

    form = client.get(url_for('auth.login_route')).forms['login_form']
    form['username'] = webauthn_credential.user.username
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = response.follow()
    form = response.forms['webauthn_login_form']
    form['assertion'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Login error during Webauthn authentication.\');")]')


def test_login_oidc_route(client, user):
    """test_login_oidc_route"""

    authorize_redirect_mock = Mock(return_value=redirect('fake_redir_to_idp'))
    authorize_access_token_mock = Mock(return_value={'userinfo': {'email': user.email}})

    patch_oauth_redirect = patch.object(oauth.OIDC_DEFAULT, 'authorize_redirect', authorize_redirect_mock)
    patch_oauth_token = patch.object(oauth.OIDC_DEFAULT, 'authorize_access_token', authorize_access_token_mock)
    with patch_oauth_redirect, patch_oauth_token:
        response = client.get(url_for('auth.login_oidc_route'))
        assert response.status_code == HTTPStatus.FOUND
        assert response.headers['Location'] == 'fake_redir_to_idp'

        response = client.get(url_for('auth.login_oidc_callback_route'))
        assert response.status_code == HTTPStatus.FOUND
        assert response.headers['Location'] == url_for('index_route')

    authorize_redirect_mock.assert_called_once()
    authorize_access_token_mock.assert_called_once()


def test_login_oidc_route_noexist_user(client):
    """test non-existing user"""

    authorize_access_token_mock = Mock(return_value={'userinfo': {'email': 'notexist'}})

    patch_oauth_token = patch.object(oauth.OIDC_DEFAULT, 'authorize_access_token', authorize_access_token_mock)
    with patch_oauth_token:
        response = client.get(url_for('auth.login_oidc_callback_route'))
        assert response.status_code == HTTPStatus.FOUND
        assert response.headers['Location'] == url_for('auth.login_route')

    authorize_access_token_mock.assert_called_once()


def test_login_oidc_route_disabled_oidc(client):
    """test disabled oidc redirects"""

    current_app.config['OIDC_NAME'] = None

    response = client.get(url_for('auth.login_oidc_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers['Location'] == url_for('auth.login_route')

    response = client.get(url_for('auth.login_oidc_callback_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert response.headers['Location'] == url_for('auth.login_route')


def test_login_oidc_route_handle_oidc_errors(client):
    """test_login_oidc_route"""

    authorize_redirect_mock = Mock(side_effect=AuthlibBaseError)
    authorize_access_token_mock = Mock(side_effect=AuthlibBaseError)

    patch_oauth_redirect = patch.object(oauth.OIDC_DEFAULT, 'authorize_redirect', authorize_redirect_mock)
    patch_oauth_token = patch.object(oauth.OIDC_DEFAULT, 'authorize_access_token', authorize_access_token_mock)

    with patch_oauth_redirect, patch_oauth_token:
        response = client.get(url_for('auth.login_oidc_route'))
        assert response.status_code == HTTPStatus.FOUND
        assert response.headers['Location'] == url_for('auth.login_route')
        response = response.follow()
        assert response.status_code == HTTPStatus.OK
        assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'OIDC Authentication error\');")]')

        response = client.get(url_for('auth.login_oidc_callback_route'))
        assert response.status_code == HTTPStatus.FOUND
        assert response.headers['Location'] == url_for('auth.login_route')
        response = response.follow()
        assert response.status_code == HTTPStatus.OK
        assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'OIDC Authentication error\');")]')

    authorize_redirect_mock.assert_called_once()
    authorize_access_token_mock.assert_called_once()
