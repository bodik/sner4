# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage jumper
"""

from http import HTTPStatus
from ipaddress import ip_address

from flask import jsonify, url_for
from sqlalchemy import or_

from sner.server.auth.core import session_required
from sner.server.storage.forms import QuickjumpForm
from sner.server.storage.models import Host
from sner.server.storage.views import blueprint


@blueprint.route('/quickjump', methods=['POST'])
@session_required('operator')
def quickjump_route():
    """
    returns url for quick jump via simple query-string
    """

    form = QuickjumpForm()
    if form.validate_on_submit():
        try:
            address = str(ip_address(form.quickjump.data))
        except ValueError:
            address = None
        host = Host.query.filter(or_(Host.address == address, Host.hostname.ilike(f"{form.quickjump.data}%"))).first()
        if host:
            return jsonify({'title': 'success', 'url': url_for('storage.host_view_route', host_id=host.id)})

        if form.quickjump.data.isnumeric():
            return jsonify({'title': 'success', 'url': url_for('storage.service_list_route', filter=f"Service.port==\"{form.quickjump.data}\"")})

        # TODO: refactor title to message field name
        return jsonify({'title': 'Not found'}), HTTPStatus.NOT_FOUND

    return jsonify({'title': 'Invalid request'}), HTTPStatus.BAD_REQUEST
