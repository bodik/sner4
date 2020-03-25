# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth views
"""

from flask import Blueprint


blueprint = Blueprint('auth', __name__)  # pylint: disable=invalid-name


import sner.server.auth.views.login  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.auth.views.profile  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.auth.views.user  # noqa: E402,F401  pylint: disable=wrong-import-position
