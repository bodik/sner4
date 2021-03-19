# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import re
import sys
from pprint import pprint
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParsedHost, ParsedItemsDb, ParsedNote, ParsedService, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """jarm output parser"""

    ARCHIVE_PATHS = r'output-[0-9]+.out'

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        with ZipFile(path) as fzip:
            for fname in filter(lambda x: re.match(cls.ARCHIVE_PATHS, x), fzip.namelist()):
                pidb += cls._parse_data(file_from_zip(path, fname).decode('utf-8'))

        return pidb

    @staticmethod
    def _parse_data(data):
        """parse raw string data"""

        pidb = ParsedItemsDb()

        host = None
        service = None
        via_target = None
        note = None

        for line in data.splitlines():
            if line.startswith('Domain:'):
                via_target = line.split(' ')[-1]

            if line.startswith('Resolved IP:'):
                address = line.split(' ')[-1]
                host = ParsedHost(address=address)

            if host and line.startswith('Port:'):
                port = line.split(' ')[-1]
                service = ParsedService(host_handle=host.handle, proto='tcp', port=port)

            if service and line.startswith('JARM:'):
                jarm = line.split(' ')[-1]
                if jarm != '00000000000000000000000000000000000000000000000000000000000000':
                    note = ParsedNote(host_handle=host.handle, service_handle=service.handle, via_target=via_target, xtype='jarm.fp', data=jarm)

        if host and service and note:
            pidb.hosts.upsert(host)
            pidb.services.upsert(service)
            pidb.notes.upsert(note)
        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
