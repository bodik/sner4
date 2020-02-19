# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller visuals main module
"""

from flask import Blueprint


blueprint = Blueprint('visuals', __name__)  # pylint: disable=invalid-name


import sner.server.controller.visuals.dnstree  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.visuals.service_ports  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.visuals.service_infos  # noqa: E402,F401  pylint: disable=wrong-import-position
