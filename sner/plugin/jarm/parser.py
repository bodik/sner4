# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import re
import sys
from pprint import pprint
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParserBase, ParsedHost, ParsedItemsDict as Pdict, ParsedNote, ParsedService, register_parser


@register_parser('jarm')  # pylint: disable=too-few-public-methods
class JarmParser(ParserBase):
    """jarm output parser"""

    ARCHIVE_PATHS = r'output-[0-9]+.out'

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        hosts, services, notes = Pdict(), Pdict(), Pdict()

        with ZipFile(path) as fzip:
            for ftmp in [fname for fname in fzip.namelist() if re.match(cls.ARCHIVE_PATHS, fname)]:
                thosts, tservices, _, tnotes = JarmParser._parse_data(file_from_zip(path, ftmp).decode('utf-8'))
                for storage, items in [(hosts, thosts), (services, tservices), (notes, tnotes)]:
                    for item in items:
                        storage.upsert(item)

        return list(hosts.values()), list(services.values()), [], list(notes.values())

    @staticmethod
    def _parse_data(data):
        """parse raw string data"""

        host = None
        service = None
        note = None

        for line in data.splitlines():
            if line.startswith('Resolved IP:'):
                address = line.split(' ')[-1]
                host = ParsedHost(
                    handle={'host': address},
                    address=address
                )

            if host and line.startswith('Port:'):
                port = line.split(' ')[-1]
                service = ParsedService(
                    handle={'host': host.address, 'service': f'tcp/{port}'},
                    proto='tcp',
                    port=port
                )

            if service and line.startswith('JARM:'):
                jarm = line.split(' ')[-1]
                if jarm != '00000000000000000000000000000000000000000000000000000000000000':
                    note = ParsedNote(
                        handle={'host': host.address, 'service': service.handle['service'], 'note': f'jarm.fp'},
                        xtype='jarm.fp',
                        data=jarm
                    )

        if host and service and note:
            return [host], [service], [], [note]
        return [], [], [], []


if __name__ == '__main__':  # pragma: no cover
    pprint(JarmParser.parse_path(sys.argv[1]))
