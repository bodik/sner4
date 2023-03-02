# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller portmap
"""

from http import HTTPStatus

from socket import getservbyport

from flask import render_template, request
from sqlalchemy import desc, func

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.models import Host, Service
from sner.server.visuals.views import blueprint
from sner.server.utils import filter_query


VIZPORTS_LOW = 10.0
VIZPORTS_HIGH = 100.0


@blueprint.route('/portmap')
@session_required('operator')
def portmap_route():
    """visualize portmap"""

    # join allows filter over host attrs
    query = db.session.query(Service.state, func.count(Service.id).label('state_count')).join(Host) \
        .group_by(Service.state).order_by(desc('state_count'))
    if not (query := filter_query(query, request.values.get('filter'))):
        return 'Failed to filter query', HTTPStatus.BAD_REQUEST
    portstates = query.all()

    # join allows filter over host attrs
    query = db.session.query(Service.port, func.count(Service.id)).join(Host).order_by(Service.port).group_by(Service.port)
    if not (query := filter_query(query, request.values.get('filter'))):  # pragma: no cover  ; cannot test, failed by filter processing above
        return 'Failed to filter query', HTTPStatus.BAD_REQUEST
    portmap = [{'port': port, 'count': count} for port, count in query.all()]

    # compute sizing for rendered element
    lowest = min(portmap, key=lambda x: x['count'])['count'] if portmap else 0
    highest = max(portmap, key=lambda x: x['count'])['count'] if portmap else 0
    coef = (VIZPORTS_HIGH-VIZPORTS_LOW) / max(1, (highest-lowest))
    for tmp in portmap:
        tmp['size'] = VIZPORTS_LOW + ((tmp['count']-lowest)*coef)

    return render_template('visuals/portmap.html', portmap=portmap, portstates=portstates)


@blueprint.route('/portmap_portstat/<port>')
@session_required('operator')
def portmap_portstat_route(port):
    """generate port statistics fragment"""

    stats = db.session.query(Service.proto, func.count(Service.id)).join(Host) \
        .filter(Service.port == port) \
        .group_by(Service.proto).order_by(Service.proto)

    infos = db.session.query(Service.info, func.count(Service.id).label('info_count')).join(Host) \
        .filter(Service.port == port, Service.info != '', Service.info != None) \
        .group_by(Service.info).order_by(desc('info_count'))  # noqa: E501,E711  pylint: disable=singleton-comparison

    comments = db.session.query(func.distinct(Service.comment)).join(Host) \
        .filter(Service.port == port, Service.comment != '') \
        .order_by(Service.comment)

    hosts = db.session.query(Host.address, Host.hostname, Host.id).select_from(Service).outerjoin(Host) \
        .filter(Service.port == port).order_by(Host.address)

    stats = filter_query(stats, request.values.get('filter'))
    infos = filter_query(infos, request.values.get('filter'))
    comments = filter_query(comments, request.values.get('filter'))
    hosts = filter_query(hosts, request.values.get('filter'))
    if not all([stats, infos, comments, hosts]):
        return 'Failed to parse filter', HTTPStatus.BAD_REQUEST

    try:
        portname = getservbyport(int(port))
    except OSError:
        portname = ''

    return render_template(
        'visuals/portmap_portstat.html',
        port=port,
        portname=portname,
        stats=stats.all(),
        infos=infos.all(),
        hosts=hosts.all(),
        comments=comments.all()
    )
