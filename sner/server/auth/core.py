# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth module functions
"""

import os
from base64 import b32decode, b32encode
from functools import wraps
from http import HTTPStatus
from time import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.primitives.twofactor import InvalidToken as InvalidTOTPToken
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from fido2 import cbor
from fido2.webauthn import AttestedCredentialData
from flask import _request_ctx_stack, current_app, g, redirect, request, url_for
from flask_login import current_user

from sner.server.auth.models import User
from sner.server.extensions import db, login_manager
from sner.server.password_supervisor import PasswordSupervisor as PWS
from sner.server.utils import valid_next_url


def regenerate_session():
    """regenerate session"""

    _request_ctx_stack.top.session = current_app.session_interface.new_session()
    if hasattr(g, 'csrf_token'):  # cleanup g, which is used by flask_wtf
        delattr(g, 'csrf_token')


def redirect_after_login():
    """handle next after successfull login"""

    if ('next' in request.args) and valid_next_url(request.args.get('next')):
        return redirect(request.args.get('next'))
    return redirect(url_for('index_route'))


@login_manager.user_loader
def user_loader(user_id):
    """flask_login user loader; user loaded from session"""

    user = User.query.filter(User.active, User.id == user_id).one_or_none()
    if user:
        g.auth_method = 'session'
        return user
    return None  # pragma: no cover  ; would require very-faked session


@login_manager.request_loader
def load_user_from_request(req):
    """api authentication; load user form request"""

    auth_header = req.headers.get('X-API-KEY')
    if auth_header:
        user = User.query.filter(User.active, User.apikey == PWS.hash_simple(auth_header)).first()
        if user:
            g.auth_method = 'apikey'
            return user
    return None


def session_required(role):
    """flask view decorator implementing role session-based authorization"""

    def _session_required(fnc):
        @wraps(fnc)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()

            if (g.auth_method != 'session') or (not current_user.has_role(role)):
                return 'Forbidden', HTTPStatus.FORBIDDEN

            return fnc(*args, **kwargs)

        return decorated_view
    return _session_required


def apikey_required(role):
    """flask view decorator implementing role token-based authorization"""

    def _apikey_required(fnc):
        @wraps(fnc)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return {'message': 'unauthorized'}, HTTPStatus.UNAUTHORIZED

            if (g.auth_method != 'apikey') or (not current_user.has_role(role)):
                return {'message': 'forbidden'}, HTTPStatus.FORBIDDEN

            return fnc(*args, **kwargs)

        return decorated_view
    return _apikey_required


def webauthn_credentials(user):
    """get and decode all credentials for given user"""
    return [AttestedCredentialData.create(**cbor.decode(cred.credential_data)) for cred in user.webauthn_credentials]


class TOTPImpl(TOTP):
    """Custom class wrapping defaults for used TOTP impl (pyca/cryptography)"""

    def __init__(self, secret):
        """initialize totp
        :param secret: secret seed in base32 encoding
        """
        super().__init__(b32decode(secret), 6, SHA1(), 30, backend=default_backend())

    @staticmethod
    def random_base32():
        """generate new secret, return base32 encoded representation"""
        return b32encode(os.urandom(20)).decode('ascii')

    def current_code(self):
        """generate current code"""
        return super().generate(time())

    def verify_code(self, code):
        """verify code"""

        try:
            super().verify(code.encode('ascii'), time())
        except InvalidTOTPToken:
            return False
        return True


class UserManager:
    """user manager"""

    @staticmethod
    def apikey_generate(user):
        """manage apikey for user"""

        apikey = PWS.generate_apikey()
        user.apikey = PWS.hash_simple(apikey)
        db.session.commit()
        return apikey

    @staticmethod
    def apikey_revoke(user):
        """manage apikey for user"""

        user.apikey = None
        db.session.commit()
