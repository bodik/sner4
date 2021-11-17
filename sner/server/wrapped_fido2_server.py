# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
yubico fido2 server wrapped for flask factory pattern delayed configuration
"""

from socket import getfqdn

from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity


class WrappedFido2Server(Fido2Server):
    """yubico fido2 server wrapped for flask factory pattern delayed configuration"""

    def __init__(self):
        """initialize with default rp name"""
        super().__init__(PublicKeyCredentialRpEntity(getfqdn(), f'{getfqdn()} RP'))

    def init_app(self, app):
        """reinitialize on factory pattern config request"""
        ident = app.config['SERVER_NAME'] or getfqdn()
        super().__init__(PublicKeyCredentialRpEntity(ident, f'{ident} RP'))
