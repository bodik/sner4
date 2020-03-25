# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals views
"""

from flask import Blueprint, render_template


blueprint = Blueprint('visuals', __name__)  # pylint: disable=invalid-name


@blueprint.route('/')
def index_route():
    """visuals index"""
    return render_template('visuals/index.html')


import sner.server.visuals.views.dnstree  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.visuals.views.portmap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.visuals.views.portinfos  # noqa: E402,F401  pylint: disable=wrong-import-position
