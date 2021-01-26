# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
password supervisor service
"""

import re
import secrets
import string
from crypt import crypt, mksalt, METHOD_SHA512  # pylint: disable=no-name-in-module
from hashlib import sha512
from hmac import compare_digest


class PasswordSupervisorResult():
    """classes wrapping password supervisor checks results"""

    def __init__(self, result, message):
        self._result = result
        self._message = message

    @property
    def is_strong(self):
        """iface getter"""
        return self._result

    @property
    def message(self):
        """getter"""
        return self._message


class PasswordSupervisor():
    """password supervisor implementation"""

    MIN_LENGTH = 10
    MIN_CLASSES = 3

    @classmethod
    def check_strength(cls, password):
        """supervisor; checks password strength against policy"""

        # length
        if len(password) < cls.MIN_LENGTH:
            return PasswordSupervisorResult(False, f'Password too short. At least {cls.MIN_LENGTH} characters required.')

        # complexity
        classes = 0
        if re.search('[a-z]', password):
            classes += 1
        if re.search('[A-Z]', password):
            classes += 1
        if re.search('[0-9]', password):
            classes += 1
        if re.search('[^a-zA-Z0-9]', password):
            classes += 1
        if classes < cls.MIN_CLASSES:
            return PasswordSupervisorResult(
                False,
                f'Only {classes} character classes found. At least {cls.MIN_CLASSES} classes required (lowercase, uppercase, digits, other).'
            )

        return PasswordSupervisorResult(True, 'Password is according to policy.')

    @classmethod
    def generate(cls, length=40):
        """supervisor; generates password"""

        alphabet = string.ascii_letters + string.digits
        while True:
            ret = ''.join(secrets.choice(alphabet) for i in range(length))
            if cls.check_strength(ret).is_strong:
                break
        return ret

    @staticmethod
    def generate_apikey():
        """supervisor; generate new apikey"""
        return secrets.token_hex(32)

    @staticmethod
    def hash(value, salt=None):
        """encoder; hash password with algo"""
        return crypt(value, salt if salt else mksalt(METHOD_SHA512))

    @staticmethod
    def get_salt(value):
        """encoder; demerge salt from value"""
        return value[:value.rfind('$')] if value else None

    @staticmethod
    def compare(value1, value2):
        """encoder; compare hashes"""
        return compare_digest(value1, value2) if isinstance(value1, str) and isinstance(value2, str) else False

    @staticmethod
    def hash_simple(value):
        """encoder; create non salted hash"""
        return sha512(value.encode('utf-8')).hexdigest()
