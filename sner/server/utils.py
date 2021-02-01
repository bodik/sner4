# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc utils used in server
"""

import datetime
import json
import re
from abc import ABC, abstractmethod
from ipaddress import ip_address, ip_network
from urllib.parse import urlunparse, urlparse

import yaml
from flask import current_app, request
from werkzeug.exceptions import HTTPException

from sner.agent.modules import SERVICE_TARGET_REGEXP
from sner.server.scheduler.models import Excl, ExclFamily
from sner.server.storage.models import SeverityEnum


class ExclMatcher():
    """object matching value againts set of exclusions/rules"""

    MATCHERS = {}

    @staticmethod
    def register(family):
        """register matcher class to the excl.family"""

        def register_real(cls):
            if cls not in ExclMatcher.MATCHERS:
                ExclMatcher.MATCHERS[family] = cls
            return cls
        return register_real

    def __init__(self):
        self.excls = []
        for excl in Excl.query.all():
            self.excls.append(ExclMatcher.MATCHERS[excl.family](excl.value))

    def match(self, value):
        """match value against all exclusions/matchers"""

        for excl in self.excls:
            if excl.match(value):
                return True
        return False


class ExclMatcherImplInterface(ABC):  # pylint: disable=too-few-public-methods
    """base interface which must  be implemented by all available matchers"""

    @abstractmethod
    def __init__(self, match_to):
        """constructor"""

    @abstractmethod
    def match(self, value):
        """returns bool if value matches the initialized match_to"""


@ExclMatcher.register(ExclFamily.network)  # pylint: disable=too-few-public-methods
class ExclNetworkMatcher(ExclMatcherImplInterface):
    """network matcher"""

    def __init__(self, match_to):  # pylint: disable=super-init-not-called
        self.match_to = ip_network(match_to)

    def match(self, value):
        try:
            return ip_address(value) in self.match_to
        except ValueError:
            pass

        try:
            mtmp = re.match(SERVICE_TARGET_REGEXP, value)
            if mtmp:
                return ip_address(mtmp.group('host').replace('[', '').replace(']', '')) in self.match_to
        except ValueError:
            pass

        return False


@ExclMatcher.register(ExclFamily.regex)  # pylint: disable=too-few-public-methods
class ExclRegexMatcher(ExclMatcherImplInterface):
    """regex matcher"""

    def __init__(self, match_to):  # pylint: disable=super-init-not-called
        self.match_to = re.compile(match_to)

    def match(self, value):
        return bool(self.match_to.search(value))


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
