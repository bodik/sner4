"""auth component models"""

from crypt import crypt, mksalt, METHOD_SHA512  # pylint: disable=no-name-in-module
from hmac import compare_digest

import flask_login
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property

from sner.server import db


class User(db.Model, flask_login.UserMixin):
    """user model"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    _password = db.Column('password', db.String(256))
    email = db.Column(db.String(256))
    active = db.Column(db.Boolean)
    roles = db.Column(postgresql.ARRAY(db.String, dimensions=1))

    @property
    def is_active(self):
        """user active getter"""

        return self.active

    def has_role(self, role):
        """shortcut function to check user has role"""

        if self.roles and (role in self.roles):
            return True
        return False

    @hybrid_property
    def password(self):
        """password getter"""

        return self._password

    @password.setter
    def password(self, value):
        """password setter"""

        if value:
            self._password = crypt(value, mksalt(METHOD_SHA512))

    @property
    def password_salt(self):
        """demerges salt from password"""

        return self._password[:self.password.rfind('$')] if self._password else None

    def compare_password(self, password):
        """compare user password"""

        return compare_digest(crypt(password, self.password_salt), self.password) if self.password_salt else False
