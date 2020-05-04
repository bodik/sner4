# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth test models
"""

from factory import LazyAttribute, post_generation, SubFactory
from fido2 import cbor
from soft_webauthn import SoftWebauthnDevice

from sner.server.auth.models import User, WebauthnCredential
from sner.server.extensions import webauthn
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests import BaseModelFactory


class UserFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test user model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test user model factory"""
        model = User

    username = 'user1'
    password = LazyAttribute(lambda x: PWS().generate())
    active = True
    roles = ['user']


class WebauthnCredentialFactory(BaseModelFactory):  # pylint: disable=too-few-public-methods
    """test webauthn_credential model factory"""
    class Meta:  # pylint: disable=too-few-public-methods
        """test webauthn_credential model factory"""
        model = WebauthnCredential

    user = SubFactory(UserFactory)
    user_handle = 'dummy'
    credential_data = b'dummy'
    name = 'testcredential'

    @post_generation
    def initialized_device(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """DI or self initialize device"""

        if extracted:
            device = extracted
        else:
            device = SoftWebauthnDevice()
            device.cred_init(webauthn.rp.id, b'randomhandle')

        self.user_handle = device.user_handle
        self.credential_data = cbor.encode(device.cred_as_attested().__dict__)
