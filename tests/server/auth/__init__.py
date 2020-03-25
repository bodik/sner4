# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth shared functions
"""

from fido2 import cbor
from soft_webauthn import SoftWebauthnDevice

from sner.server.auth.models import WebauthnCredential
from sner.server.extensions import webauthn
from tests import persist_and_detach


def webauthn_device_init(a_test_user):
    """initialize webauthn authenticator"""

    device = SoftWebauthnDevice()
    device.cred_init(webauthn.rp.id, b'randomhandle')
    persist_and_detach(WebauthnCredential(
        user=a_test_user,
        user_handle=device.user_handle,
        credential_data=cbor.encode(device.cred_as_attested().__dict__)))
    return device
