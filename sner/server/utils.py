# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc utils used in server
"""

import datetime
import json
from urllib.parse import urlunparse, urlparse

import yaml
from flask import current_app, request, jsonify
from lark.exceptions import LarkError
from sqlalchemy_filters import apply_filters
from werkzeug.exceptions import HTTPException

from sner.server.scheduler.core import ExclFamily
from sner.server.sqlafilter import FILTER_PARSER
from sner.server.storage.models import SeverityEnum


class SnerJSONEncoder(json.JSONEncoder):
    """Custom encoder to handle serializations of various types used within the project"""

    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, (ExclFamily, SeverityEnum, datetime.timedelta)):
            return str(o)

        if isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%dT%H:%M:%S')

        return super().default(o)  # pragma: no cover  ; no such elements


def relative_referrer():
    """makes relative relative from absolute"""

    if request.referrer:
        url = urlparse(request.referrer)
        return urlunparse(('', '', url.path, url.params, url.query, url.fragment))
    return None


def valid_next_url(nexturl):
    """validates next= and return_url= urls"""

    url = urlparse(nexturl)

    # accept only relative URLs
    if url.scheme or url.netloc:
        return False

    # validate for current application, cope with application_root, but only path not the query params
    path = url.path
    if current_app.config['APPLICATION_ROOT'] != '/':  # pragma: no cover  ; unable to test
        path = path.replace(current_app.config['APPLICATION_ROOT'], '', 1)
    try:
        current_app.url_map.bind('').match(path)
    except HTTPException:
        return False

    return True


def yaml_dump(data):
    """dump data with style"""
    return yaml.dump(data, sort_keys=False, indent=4, width=80)


def windowed_query(query, column, windowsize=5000):
    """"
    Break a Query into chunks on a given column.
    https://github.com/sqlalchemy/sqlalchemy/wiki/RangeQuery-and-WindowedRangeQuery
    """

    single_entity = query.is_single_entity
    query = query.add_columns(column).order_by(column)
    last_id = None

    while True:
        subq = query
        if last_id is not None:
            subq = subq.filter(column > last_id)
        chunk = subq.limit(windowsize).all()
        if not chunk:
            break
        last_id = chunk[-1][-1]
        for row in chunk:
            if single_entity:
                yield row[0]
            else:
                yield row[0:-1]


def filter_query(query, qfilter):
    """filter sqla query"""

    if not qfilter:
        return query

    try:
        query = apply_filters(query, FILTER_PARSER.parse(qfilter), do_auto_join=False)
    except LarkError as exc:
        if current_app.config['DEBUG']:  # pragma: no cover  ; wont debug logging coverage
            raise
        current_app.logger.error('failed to parse filer: %s', str(exc).split('\n', maxsplit=1)[0])
        return None

    return query


def json_data_response(data, status_code=200):
    """Returns a JSON data response following the Google JSON Style Guide."""
    return jsonify({
        'apiVersion': "2.0",
        'data': data
    }), status_code


def json_error_response(message, status_code):
    """Returns a JSON error response following the Google JSON Style Guide."""
    return jsonify({
        'apiVersion': "2.0",
        'error': {
            'code': status_code,
            'message': message
        }
    }), status_code
