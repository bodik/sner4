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
from sner.server.parser import ParserBase, ParsedHost, ParsedItemsDict as Pdict, ParsedNote, ParsedService


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nmap xml output parser"""

    ARCHIVE_PATHS = r'output\.xml|output6\.xml'

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        if is_zip(path):
            hosts, services, vulns, notes = Pdict(), Pdict(), Pdict(), Pdict()

            with ZipFile(path) as fzip:
                for ftmp in [fname for fname in fzip.namelist() if re.match(cls.ARCHIVE_PATHS, fname)]:
                    thosts, tservices, tvulns, tnotes = cls._parse_data(file_from_zip(path, ftmp).decode('utf-8'))
                    for storage, items in [(hosts, thosts), (services, tservices), (vulns, tvulns), (notes, tnotes)]:
                        for item in items:
                            storage.upsert(item)

            return list(hosts.values()), list(services.values()), list(vulns.values()), list(notes.values())

        return cls._parse_data(Path(path).read_text())

    @classmethod
    def _parse_data(cls, data):
        """parse raw string data"""

        report = libnmap.parser.NmapParser.parse_fromstring(data)

        hosts = cls._parse_hosts(report)
        services = cls._parse_services(report)
        vulns = []
        notes = cls._parse_notes(report)

        return hosts, services, vulns, notes

    @staticmethod
    def _parse_hosts(report):
        """parse hosts"""

        hosts = []

        for ihost in report.hosts:
            host = ParsedHost(handle={'host': ihost.address}, address=ihost.address)

            if ihost.hostnames:
                host.hostnames = list(set(ihost.hostnames))
                if not host.hostname:
                    host.hostname = host.hostnames[0]

            for osmatch in ihost.os_match_probabilities():
                if osmatch.accuracy == 100:
                    host.os = osmatch.name

            hosts.append(host)

        return hosts

    @staticmethod
    def _parse_services(report):
        """parse services"""

        services = []

        for ihost in report.hosts:
            for iservice in ihost.services:

                service = ParsedService(
                    handle={'host': ihost.address, 'service': f'{iservice.protocol}/{iservice.port}'},
                    proto=iservice.protocol,
                    port=iservice.port,
                    state=f'{iservice.state}:{iservice.reason}',
                    import_time=datetime.fromtimestamp(int(ihost.starttime))
                )
                if iservice.service:
                    service.name = iservice.service
                if iservice.banner:
                    service.info = iservice.banner

                services.append(service)

        return services

    @staticmethod
    def _parse_notes(report):
        """parse notes"""

        notes = []

        for ihost in report.hosts:
            # host level scripts
            for iscript in ihost.scripts_results:
                notes.append(ParsedNote(
                    handle={'host': ihost.address, 'note': f'nmap.{iscript["id"]}'},
                    xtype=f'nmap.{iscript["id"]}',
                    data=json.dumps(iscript),
                    import_time=datetime.fromtimestamp(int(ihost.starttime))
                ))

            # service level scripts
            for iservice in ihost.services:
                for iscript in iservice.scripts_results:
                    notes.append(ParsedNote(
                        handle={'host': ihost.address, 'service': f'{iservice.protocol}/{iservice.port}', 'note': f'nmap.{iscript["id"]}'},
                        xtype=f'nmap.{iscript["id"]}',
                        data=json.dumps(iscript),
                        import_time=datetime.fromtimestamp(int(ihost.starttime))
                    ))

        return notes


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
