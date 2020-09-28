# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller portinfos
"""

from flask import jsonify, render_template, request
from sqlalchemy import desc, func
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.sqlafilter import filter_parser
from sner.server.storage.views.service import service_info_column
from sner.server.storage.models import Host, Service
from sner.server.visuals.views import blueprint


@blueprint.route('/portinfos')
@role_required('operator')
def portinfos_route():
    """generate word cloud for service.info"""

    return render_template('visuals/portinfos.html')


@blueprint.route('/portinfos.json')
@role_required('operator')
def portinfos_json_route():
    """service info visualization json data endpoint"""

    info_column = service_info_column(request.args.get('crop'))
    query = db.session.query(info_column.label('info'), func.count(Service.id).label('info_count')).join(Host) \
        .filter(Service.info != '', Service.info != None).group_by(info_column).order_by(desc('info_count'))  # noqa: E501,E711  pylint: disable=singleton-comparison

    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)
    if request.values.get('limit'):
        query = query.limit(request.values.get('limit'))

    return jsonify([{'info': info, 'count': count} for info, count in query.all()])
