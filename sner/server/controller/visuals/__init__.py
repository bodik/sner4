# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller visuals main module
"""

from flask import Blueprint, render_template


blueprint = Blueprint('visuals', __name__)  # pylint: disable=invalid-name


@blueprint.route('/')
def index_route():
    """visuals index"""
    return render_template('visuals/index.html')


import sner.server.controller.visuals.dnstree  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.visuals.portmap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.visuals.portinfos  # noqa: E402,F401  pylint: disable=wrong-import-position
