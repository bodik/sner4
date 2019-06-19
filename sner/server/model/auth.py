"""auth component models"""

import flask_login
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property

from sner.server import db
from sner.server.password_supervisor import PasswordSupervisor as PWS


class User(db.Model, flask_login.UserMixin):
    """user model"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), unique=True, nullable=False)
    _password = db.Column('password', db.String(256))
    _apikey = db.Column('apikey', db.String(256))
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
        """password setter; condition is handling value edit from empty form.populate_obj submission"""

        if value:
            self._password = PWS().hash(value)

    @hybrid_property
    def apikey(self):
        """apikey getter"""

        return self._apikey

    @apikey.setter
    def apikey(self, value):
        """apikey setter"""

        self._apikey = PWS.hash_simple(value) if value else None