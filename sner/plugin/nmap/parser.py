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
from time import time
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
            host, cpe_note = cls._parse_host(ihost)
            via_target = ihost.user_target_hostname or host.address
            import_time = datetime.fromtimestamp(int(ihost.starttime or time()))
            pidb.hosts.upsert(host)
            if cpe_note:
                pidb.notes.upsert(cpe_note)

            for iscript in ihost.scripts_results:
                note = cls._parse_note(iscript, host.handle, None, via_target, import_time)
                pidb.notes.upsert(note)

            for iservice in ihost.services:
                service = cls._parse_service(iservice, host.handle, import_time)
                pidb.services.upsert(service)

                if iservice.cpelist:
                    note = ParsedNote(
                        host_handle=host.handle,
                        service_handle=service.handle,
                        via_target=via_target,
                        xtype='cpe',
                        data=json.dumps([x.cpestring for x in iservice.cpelist]),
                        import_time=import_time
                    )
                    pidb.notes.upsert(note)

                for iscript in iservice.scripts_results:
                    note = cls._parse_note(iscript, host.handle, service.handle, via_target, import_time)
                    pidb.notes.upsert(note)

        return pidb

    @staticmethod
    def _parse_host(ihost):
        """parse host"""

        host = ParsedHost(address=ihost.address)
        cpe_note = None

        if ihost.hostnames:
            host.hostnames = list(set(ihost.hostnames))
            if not host.hostname:
                host.hostname = host.hostnames[0]

        for osmatch in ihost.os_match_probabilities():
            if osmatch.accuracy == 100:
                host.os = osmatch.name
                cpe_note = ParsedNote(host_handle=host.handle, xtype='cpe', data=json.dumps(osmatch.get_cpe()))

        return host, cpe_note

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
    def _parse_note(iscript, host_handle, service_handle, via_target, import_time):
        """parse note"""

        return ParsedNote(
            host_handle=host_handle,
            service_handle=service_handle,
            via_target=via_target,
            xtype=f'nmap.{iscript["id"]}',
            data=json.dumps(iscript),
            import_time=import_time
        )


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]).__dict__)
