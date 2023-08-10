# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers core objects

The parser subsystem is responsible for parsing data from various scanning
tools. Parsers should be implemented via sner.plugin package and must
implement ParserBase interface.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from pathlib import Path

from littletable import Table as LittleTable

import sner.plugin
from sner.lib import ZipFile, file_from_zip, is_zip


REGISTERED_PARSERS = {}


def load_parser_plugins():
    """load all parser plugins/modules"""

    for plugin_path in Path(sner.plugin.__file__).parent.glob('*/parser.py'):
        plugin_name = plugin_path.parent.name
        module = import_module(f'sner.plugin.{plugin_name}.parser')
        REGISTERED_PARSERS[plugin_name] = getattr(module, 'ParserModule')


def auto_detect_parser(path):
    """tries automatically detect parser"""
    parser = None

    if is_zip(path):
        with ZipFile(path) as fzip:
            for fname in filter(lambda x: x == 'assignment.json', fzip.namelist()):
                try:
                    parser = json.loads(file_from_zip(path, fname).decode('utf-8'))['config']['module']
                except KeyError:
                    pass
    else:
        output = Path(path).read_text(encoding='utf-8')

        # tries to detect the parser based on the output
        if '<!DOCTYPE nmaprun>' in output:
            parser = 'nmap'
        elif '<NessusClientData_v2>' in output:
            parser = 'nessus'
        elif 'testssl.sh' in output:
            parser = 'testssl'

    return parser


class ParsedItemBase:  # pylint: disable=too-few-public-methods
    """parsed items base object; shared functions"""

    def update(self, obj):
        """update data from other object"""

        for key, value in obj.__dict__.items():
            # do not overwrite with None value
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
    iid: int = None  # primary key
    hostname: str = None
    hostnames: list = None
    os: str = None  # pylint: disable=invalid-name


@dataclass
class ParsedService(ParsedItemBase):  # pylint: disable=too-many-instance-attributes
    """parsed service"""

    host_iid: int
    proto: str
    port: int
    iid: int = None  # primary key
    state: str = None
    name: str = None
    info: str = None
    import_time: datetime = None


@dataclass
class ParsedVuln(ParsedItemBase):  # pylint: disable=too-many-instance-attributes
    """parsed vuln"""

    host_iid: int
    name: str
    xtype: str
    service_iid: int = None
    via_target: str = None
    iid: int = None  # primary key
    severity: str = None
    descr: str = None
    data: str = None
    refs: list = None
    import_time: datetime = None


@dataclass
class ParsedNote(ParsedItemBase):
    """parsed note"""

    host_iid: int
    xtype: str
    service_iid: tuple = None
    via_target: str = None
    iid: int = None  # primary key
    data: str = None
    import_time: datetime = None


class ParsedItemsDb:
    """container for parsed items"""

    def __init__(self):
        self.hosts = LittleTable()
        self.hosts.create_index('iid', unique=True)
        self.services = LittleTable()
        self.services.create_index('iid', unique=True)
        self.vulns = LittleTable()
        self.vulns.create_index('iid', unique=True)
        self.notes = LittleTable()
        self.notes.create_index('iid', unique=True)

    @staticmethod
    def _first(alist):
        if alist:
            return alist[0]
        return None

    def upsert_host(self, address, **kwargs):
        """upsert host"""

        host = ParsedHost(address, **kwargs)

        pidb_host = self._first(self.hosts.where(address=host.address))
        if pidb_host:
            pidb_host.update(host)
            return pidb_host

        host.iid = len(self.hosts)
        self.hosts.insert(host)
        return host

    def upsert_service(self, host_address, proto, port, **kwargs):
        """upsert service"""

        pidb_host = self.upsert_host(host_address)
        service = ParsedService(pidb_host.iid, proto, port, **kwargs)

        pidb_service = self._first(self.services.where(host_iid=service.host_iid, proto=service.proto, port=service.port))
        if pidb_service:
            pidb_service.update(service)
            return pidb_service

        service.iid = len(self.services)
        self.services.insert(service)
        return service

    def upsert_vuln(self, host_address, name, xtype, service_proto=None, service_port=None, via_target=None, **kwargs):  # noqa: E501  pylint: disable=too-many-arguments
        """upsert vuln"""

        pidb_host = self.upsert_host(host_address)
        pidb_service = self.upsert_service(host_address, service_proto, service_port) if (service_proto and service_port) else None
        vuln = ParsedVuln(pidb_host.iid, name, xtype, service_iid=pidb_service.iid if pidb_service else None, via_target=via_target, **kwargs)

        pidb_vuln = self._first(self.vulns.where(
            host_iid=vuln.host_iid,
            name=vuln.name,
            xtype=vuln.xtype,
            service_iid=vuln.service_iid,
            via_target=vuln.via_target
        ))
        if pidb_vuln:
            pidb_vuln.update(vuln)
            return pidb_vuln

        vuln.iid = len(self.vulns)
        self.vulns.insert(vuln)
        return vuln

    def upsert_note(self, host_address, xtype, service_proto=None, service_port=None, via_target=None, **kwargs):  # noqa: E501  pylint: disable=too-many-arguments
        """upsert vuln"""

        pidb_host = self.upsert_host(host_address)
        pidb_service = self.upsert_service(host_address, service_proto, service_port) if (service_proto and service_port) else None
        note = ParsedNote(pidb_host.iid, xtype, service_iid=pidb_service.iid if pidb_service else None, via_target=via_target, **kwargs)

        pidb_note = self._first(self.notes.where(host_iid=note.host_iid, xtype=note.xtype, service_iid=note.service_iid, via_target=note.via_target))
        if pidb_note:
            pidb_note.update(note)
            return pidb_note

        note.iid = len(self.notes)
        self.notes.insert(note)
        return note


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
