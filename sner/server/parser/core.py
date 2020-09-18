# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers core objects
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class ParsedItemsDict(dict):
    """parsed items; used to merge parsed items with the same handle"""

    def upsert(self, item):
        """insert or update existing object by .handle key"""

        if item.hash() not in self:
            self[item.hash()] = item
        else:
            self[item.hash()].update(item)


@dataclass
class ParsedItemBase(ABC):
    """
    Parsed items base class. All parsed items attributes should corespond with storage.model.
    'handle' is a dict of related model identifiers used for merge same objects from several
    distinct agent outputs.
    """

    handle: dict

    def update(self, obj):
        """update from other object"""

        for key, value in obj.__dict__.items():
            # do not overwrite with None
            if value is None:
                continue

            # merge lists
            if isinstance(value, list):
                new_value = (getattr(self, key) or []) + value
                setattr(self, key, new_value)
                continue

            # set new value
            setattr(self, key, value)

    def hash(self):
        """produce hashed handle for use as a dict key"""
        return hash(json.dumps(self.handle, sort_keys=True))


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
