# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers core objects

The parser subsystem is responsible for parsing data from various scanning
tools. Parsers should come via sner.plugin package and each parser must
implement ParserBase interface.
"""

from abc import ABC, abstractmethod
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from pathlib import Path

import sner.plugin


REGISTERED_PARSERS = {}

HostHandle = namedtuple('HostHandle', ['address'])
ServiceHandle = namedtuple('ServiceHandle', ['host', 'proto', 'port'])
DataHandle = namedtuple('DataHandle', ['host', 'service', 'xtype'])


def load_parser_plugins():
    """load all parser plugins/modules"""

    for plugin_path in Path(sner.plugin.__file__).parent.glob('*/parser.py'):
        plugin_name = plugin_path.parent.name
        module = import_module(f'sner.plugin.{plugin_name}.parser')
        REGISTERED_PARSERS[plugin_name] = getattr(module, 'ParserModule')


class ParsedItemsTable(dict):
    """parsed items dict"""

    def upsert(self, item):
        """insert or update existing object by id"""

        if item.handle in self:
            self[item.handle].update(item)
        else:
            self[item.handle] = item


class ParsedItemsDb:  # pylint: disable=too-few-public-methods
    """container for parsed items"""

    def __init__(self):
        self.hosts = ParsedItemsTable()
        self.services = ParsedItemsTable()
        self.vulns = ParsedItemsTable()
        self.notes = ParsedItemsTable()

    def __add__(self, obj):
        """merge all containers from other pi"""

        for key in self.__dict__:
            for item in getattr(obj, key).values():
                getattr(self, key).upsert(item)
        return self


class ParsedItemBase:  # pylint: disable=too-few-public-methods
    """parsed items base object; shared functions"""

    def update(self, obj):
        """update data from other object"""

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


@dataclass
class ParsedHost(ParsedItemBase):
    """parsed host"""

    address: str
    hostname: str = None
    hostnames: list = None
    os: str = None  # pylint: disable=invalid-name

    @property
    def handle(self):
        """return item reference handle"""
        return HostHandle(self.address)


@dataclass
class ParsedService(ParsedItemBase):
    """parsed service"""

    host_handle: tuple
    proto: str
    port: int
    state: str = None
    name: str = None
    info: str = None
    import_time: datetime = None

    @property
    def handle(self):
        """return item reference handle"""
        return ServiceHandle(self.host_handle, self.proto, self.port)


@dataclass  # pylint: disable=too-many-instance-attributes
class ParsedVuln(ParsedItemBase):
    """parsed vuln"""

    host_handle: tuple
    name: str
    xtype: str
    service_handle: tuple = None
    severity: str = None
    descr: str = None
    data: str = None
    refs: list = None
    import_time: datetime = None

    @property
    def handle(self):
        """return item reference handle"""
        return DataHandle(self.host_handle, self.service_handle, self.xtype)


@dataclass
class ParsedNote(ParsedItemBase):
    """parsed note"""

    host_handle: tuple
    xtype: str
    service_handle: tuple = None
    data: str = None
    import_time: datetime = None

    @property
    def handle(self):
        """return item reference handle"""
        return DataHandle(self.host_handle, self.service_handle, self.xtype)


class ParserBase(ABC):  # pylint: disable=too-few-public-methods
    """parser interface definition"""

    @staticmethod
    @abstractmethod
    def parse_path(path):
        """
        Parse data from path. Must parse .zip archive produced by respective
        agent module. Optionaly can parse also raw output from external tool.

        :return: pseudo database of parsed objects (hosts, services, vulns, notes)
        :rtype: ParsedItemsDb
        """
