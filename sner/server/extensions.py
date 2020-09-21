# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
app extensions module
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from sner.server.flask_jsglue import JSGlue
from sner.server.wrapped_fido2_server import WrappedFido2Server


db = SQLAlchemy()  # pylint: disable=invalid-name
jsglue = JSGlue()  # pylint: disable=invalid-name
login_manager = LoginManager()  # pylint: disable=invalid-name
webauthn = WrappedFido2Server()  # pylint: disable=invalid-name
