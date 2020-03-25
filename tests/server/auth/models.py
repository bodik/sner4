# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth test models
"""

import pytest
from fido2 import cbor
from soft_webauthn import SoftWebauthnDevice

from sner.server.auth.models import User, WebauthnCredential
from sner.server.extensions import webauthn
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
    device.cred_init(webauthn.rp.id, b'randomhandle')
    return WebauthnCredential(
        user_id=a_test_user.id,
        user=a_test_user,
        user_handle=device.user_handle,
        credential_data=cbor.encode(device.cred_as_attested().__dict__),
        name='testcredential')


@pytest.fixture
def test_user(app):  # pylint: disable=unused-argument
    """persistent test user"""

    yield persist_and_detach(create_test_user())


@pytest.fixture
def test_wncred(test_user):  # pylint: disable=redefined-outer-name
    """persistent test registered webauthn credential"""

    yield persist_and_detach(create_test_wncred(test_user))
