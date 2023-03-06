# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller internals
"""

from flask import render_template

from sner.server.auth.core import session_required
from sner.server.visuals.views import blueprint


@blueprint.route('/internals')
@session_required('admin')
def internals_route():
    """show various internals"""

    return render_template('visuals/internals.html')
