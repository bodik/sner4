# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

from zipfile import ZipFile
from pathlib import Path

from sner.lib import file_from_zip, is_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """icmp up parser"""

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        if is_zip(path):
            with ZipFile(path) as fzip:
                for fname in filter(lambda x: 'output' == x, fzip.namelist()):
                    pidb = cls._parse_data(file_from_zip(path, fname).decode('utf-8'), pidb)

            return pidb
        return cls._parse_data(Path(path).read_text(encoding='utf-8'), pidb)

    @classmethod
    def _parse_data(cls, data, pidb):
        for line in data.splitlines():
            ip_address, status = line.split(" ")

            if status == 'UP':
                pidb.upsert_host(ip_address)
                pidb.upsert_note(ip_address, 'icmp_up', data="Host is up")

        return pidb
