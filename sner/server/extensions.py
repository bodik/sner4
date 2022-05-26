# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
app extensions module
"""

from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

from sner.server.flask_jsglue import JSGlue
from sner.server.wrapped_fido2_server import WrappedFido2Server


api = Api()  # pylint: disable=invalid-name
db = SQLAlchemy()  # pylint: disable=invalid-name
jsglue = JSGlue()  # pylint: disable=invalid-name
login_manager = LoginManager()  # pylint: disable=invalid-name
migrate = Migrate()  # pylint: disable=invalid-name
oauth = OAuth()  # pylint: disable=invalid-name
webauthn = WrappedFido2Server()  # pylint: disable=invalid-name
