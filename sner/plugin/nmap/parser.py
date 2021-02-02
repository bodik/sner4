# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint
from zipfile import ZipFile

import libnmap.parser

from sner.lib import file_from_zip, is_zip
from sner.server.parser import ParsedHost, ParsedItemsDb, ParsedNote, ParsedService, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nmap xml output parser"""

    ARCHIVE_PATHS = r'output\.xml|output6\.xml'

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        if is_zip(path):
            pidb = ParsedItemsDb()

            with ZipFile(path) as fzip:
                for fname in filter(lambda x: re.match(cls.ARCHIVE_PATHS, x), fzip.namelist()):
                    pidb += cls._parse_data(file_from_zip(path, fname).decode('utf-8'))

            return pidb

        return cls._parse_data(Path(path).read_text())

    @classmethod
    def _parse_data(cls, data):
        """parse raw string data"""

        report = libnmap.parser.NmapParser.parse_fromstring(data)
        pidb = ParsedItemsDb()

        for ihost in report.hosts:
            host = cls._parse_host(ihost)
            import_time = datetime.fromtimestamp(int(ihost.starttime))
            pidb.hosts[host.handle] = host

            for iscript in ihost.scripts_results:
                note = cls._parse_note(iscript, host.handle, import_time)
                pidb.notes[note.handle] = note

            for iservice in ihost.services:
                service = cls._parse_service(iservice, host.handle, import_time)
                pidb.services[service.handle] = service

                for iscript in iservice.scripts_results:
                    note = cls._parse_note(iscript, host.handle, import_time, service.handle)
                    pidb.notes[note.handle] = note

        return pidb

    @staticmethod
    def _parse_host(ihost):
        """parse host"""

        host = ParsedHost(address=ihost.address)
        if ihost.hostnames:
            host.hostnames = list(set(ihost.hostnames))
            if not host.hostname:
                host.hostname = host.hostnames[0]

        for osmatch in ihost.os_match_probabilities():
            if osmatch.accuracy == 100:
                host.os = osmatch.name

        return host

    @staticmethod
    def _parse_service(iservice, host_handle, import_time):
        """parse service"""

        service = ParsedService(
            host_handle=host_handle,
            proto=iservice.protocol,
            port=iservice.port,
            state=f'{iservice.state}:{iservice.reason}',
            import_time=import_time
        )

        if iservice.service:
            service.name = iservice.service
        if iservice.banner:
            service.info = iservice.banner

        return service

    @staticmethod
    def _parse_note(iscript, host_handle, import_time, service_handle=None):
        """parse note"""

        return ParsedNote(
            host_handle=host_handle,
            service_handle=service_handle,
            xtype=f'nmap.{iscript["id"]}',
            data=json.dumps(iscript),
            import_time=import_time
        )


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]).__dict__)
