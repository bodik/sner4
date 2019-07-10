"""auth tests models"""

import pytest
from fido2 import cbor
from soft_webauthn import SoftWebauthnDevice

from sner.server import webauthn
from sner.server.model.auth import User, WebauthnCredential
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests import persist_and_detach


def create_test_user():
    """test user data"""

    return User(
        username='user1',
        password=PWS().generate(),
        active=True,
        roles=['user'])


def create_test_wncred(a_test_user):
    """test webauthn credential"""

    device = SoftWebauthnDevice()
    device.cred_init(webauthn.rp.ident, b'randomhandle')
    return WebauthnCredential(
        user=a_test_user,
        user_handle=device.user_handle,
        credential_data=cbor.encode(device.cred_as_attested().__dict__),
        name='testcredential')


@pytest.fixture
def test_user(app):
    """persistent test user"""

    yield persist_and_detach(create_test_user())


@pytest.fixture
def test_wncred(test_user):
    """persistent test registered webauthn credential"""

    yield persist_and_detach(create_test_wncred(test_user))
