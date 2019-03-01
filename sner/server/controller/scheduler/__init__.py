"""controller scheduler main module"""

from flask import Blueprint
blueprint = Blueprint('scheduler', __name__) # pylint: disable=invalid-name

import sner.server.controller.scheduler.job # pylint: disable=wrong-import-position
import sner.server.controller.scheduler.queue # pylint: disable=wrong-import-position
import sner.server.controller.scheduler.task # pylint: disable=wrong-import-position
