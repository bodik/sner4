"""controller scheduler main module"""

from flask import Blueprint
blueprint = Blueprint('scheduler', __name__) # pylint: disable=invalid-name

import sner.server.controller.scheduler.job
import sner.server.controller.scheduler.profile
import sner.server.controller.scheduler.task
