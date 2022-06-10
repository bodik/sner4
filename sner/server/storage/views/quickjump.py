# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage jumper
"""

from http import HTTPStatus
from ipaddress import ip_address

from flask import jsonify, request, url_for
from sqlalchemy import cast, or_

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.forms import QuickjumpForm
from sner.server.storage.models import Host
from sner.server.storage.views import blueprint


AUTOCOMPLETE_LIMIT = 10


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
            return jsonify({'message': 'success', 'url': url_for('storage.host_view_route', host_id=host.id)})

        if form.quickjump.data.isnumeric():
            return jsonify({'message': 'success', 'url': url_for('storage.service_list_route', filter=f"Service.port==\"{form.quickjump.data}\"")})

        return jsonify({'message': 'Not found'}), HTTPStatus.NOT_FOUND

    return jsonify({'message': 'Invalid request'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/quickjump_autocomplete')
@session_required('operator')
def quickjump_autocomplete_route():
    """quickjump autocomplete suggestions"""

    term = request.args.get('term', '')
    if not term:
        return jsonify([])

    data = []
    hosts = Host.query.filter(or_(cast(Host.address, db.String).ilike(f"%{term}%"), Host.hostname.ilike(f"%{term}%"))).limit(AUTOCOMPLETE_LIMIT).all()
    for host in hosts:
        if term in host.address:
            data.append(host.address)
        if term in host.hostname:
            data.append(host.hostname)

    return jsonify(data)
