"""controller scheduler main module"""

from flask import Blueprint
blueprint = Blueprint('scheduler', __name__)  # pylint: disable=invalid-name

import sner.server.controller.scheduler.job  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.scheduler.queue  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.scheduler.task  # noqa: E402,F401  pylint: disable=wrong-import-position
