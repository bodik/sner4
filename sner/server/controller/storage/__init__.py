"""controller storage main module"""

from flask import Blueprint
blueprint = Blueprint('storage', __name__) # pylint: disable=invalid-name

import sner.server.controller.storage.host # pylint: disable=wrong-import-position
import sner.server.controller.storage.service # pylint: disable=wrong-import-position
