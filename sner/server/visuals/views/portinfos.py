# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller portinfos
"""

from http import HTTPStatus

from flask import jsonify, render_template, request
from sqlalchemy import desc, func

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.views.service import service_info_column
from sner.server.storage.models import Host, Service
from sner.server.utils import filter_query
from sner.server.visuals.views import blueprint


@blueprint.route('/portinfos')
@session_required('operator')
def portinfos_route():
    """generate word cloud for service.info"""

    return render_template('visuals/portinfos.html')


@blueprint.route('/portinfos.json')
@session_required('operator')
def portinfos_json_route():
    """service info visualization json data endpoint"""

    info_column = service_info_column(request.args.get('crop'))
    # join allows filter over host attrs
    query = db.session.query(info_column.label('info'), func.count(Service.id).label('info_count')).join(Host) \
        .filter(Service.info != '', Service.info != None) \
        .group_by(info_column).order_by(desc('info_count'))  # noqa: E711  pylint: disable=singleton-comparison

    if not (query := filter_query(query, request.values.get('filter'))):
        return 'Failed to filter query', HTTPStatus.BAD_REQUEST
    if request.values.get('limit'):
        query = query.limit(request.values.get('limit'))

    return jsonify([{'info': info, 'count': count} for info, count in query.all()])
