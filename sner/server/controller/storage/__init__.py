"""controller storage main module"""

from flask import Blueprint
blueprint = Blueprint('storage', __name__)  # pylint: disable=invalid-name


import sner.server.controller.storage.host  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.service  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.note  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.vuln  # noqa: E402,F401  pylint: disable=wrong-import-position
