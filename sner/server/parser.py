# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers core objects
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


registered_parsers = {}  # pylint: disable=invalid-name


def register_parser(name):
    """register parser class to registry"""

    def register_parser_real(cls):
        if cls not in registered_parsers:
            registered_parsers[name] = cls
        return cls
    return register_parser_real


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
        Parse data from path. Must parse .zip archive produced by respective
        agent module. Optionaly can parse also raw output from external tool.

        Returns tuple of lists of Parsed* objects representing model objects
        for storage subsystem. The extra attribute `handle`, represents the
        item key attributes and it's used to bind related models and
        locate/upsert already existing items in the storage.

        ```
        def parse_path(path):
            # sample static parser

            parsed_host_1 = ParsedHost(
                handle = {'host': '192.168.0.1'}
                address = '192.168.0.1'
            )

            parsed_service_1 = ParsedService(
                handle = {'host': '192.168.0.1', 'service': 'tcp/80'},
                proto = 'tcp',
                port = '80'
            )

            parsed_vuln_1 = ParsedVuln(
                handle = {'host': '192.168.0.1', 'service': 'tcp/80', 'vuln': 'weak_pass1'},
                xtype = 'weak_pass1',
                name = 'weak password found'
            )

            parsed_note_1 = ParsedNote(
                handle = {'host': '192.168.0.1', 'service': 'tcp/80', 'note': 'jarm.fp'},
                xtype = 'jarm.fp',
                data = '123'
            )

            return [parsed_host_1], [parsed_service_1], [parsed_vuln_1], [parsed_note_1]
        ```

        :return: tuple(hosts, services, vulns, notes)
        :rtype: tuple
        """
