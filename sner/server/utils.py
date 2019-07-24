# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc utils used in server
"""

import abc
import datetime
import json
import re
from ipaddress import ip_address, ip_network

from nessus_report_parser.model.report_item import ReportItem as nessus_report_ReportItem

from sner.agent.modules import Inetverscan
from sner.server.model.scheduler import Excl, ExclFamily
from sner.server.model.storage import SeverityEnum


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


class ExclMatcherImplInterface(abc.ABC):  # pylint: disable=too-few-public-methods
    """base interface which must  be implemented by all available matchers"""

    @abc.abstractmethod
    def __init__(self, match_to):
        """constructor"""

    @abc.abstractmethod
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
            mtmp = re.match(Inetverscan.TARGET_RE, value)
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

        if isinstance(o, nessus_report_ReportItem):
            return o.__dict__

        if isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%dT%H:%M:%S')

        return super().default(o)  # pragma: no cover  ; no such elements
