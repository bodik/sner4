# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers core objects
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class ParsedItemsDict(dict):
    """parsed items; used to merge parsed items with the same handle"""

    def upsert(self, item):
        """insert or update existing object by .handle key"""

        if item.handle not in self:
            self[item.handle] = item
        else:
            self[item.handle].update(item)


@dataclass
class ParsedItemBase(ABC):
    """parsed items base"""

    handle: str

    def update(self, obj):
        """update from other object"""
        self.__dict__.update(obj.__dict__)


@dataclass
class ParsedHost(ParsedItemBase):
    """parsed host"""

    address: str
    hostname: str = None
    hostnames: list = None
    os: str = None  # pylint: disable=invalid-name


@dataclass
class ParsedService(ParsedItemBase):
    """parsed service"""

    proto: str
    port: int
    state: str = None
    name: str = None
    info: str = None
    import_time: datetime = None


@dataclass
class ParsedVuln(ParsedItemBase):
    """parsed vuln"""

    name: str
    xtype: str = None
    severity: str = None
    descr: str = None
    data: str = None
    refs: list = None
    import_time: datetime = None


@dataclass
class ParsedNote(ParsedItemBase):
    """parsed note"""

    xtype: str = None
    data: str = None
    import_time: datetime = None


class ParserBase(ABC):  # pylint: disable=too-few-public-methods
    """parser interface definition"""

    @staticmethod
    @abstractmethod
    def parse_path(path):
        """
        parse data from path

        :return: tuple(hosts, services, vulns, notes)
        :rtype: tuple
        """
