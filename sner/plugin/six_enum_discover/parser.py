# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import re
import sys
from pprint import pprint
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """six enum parser, pulls list of hosts for discovery module"""

    ARCHIVE_PATHS = r'output\-[0-9]+.txt'

    @classmethod
    def parse_path(cls, path):
        """parse path and returns list of hosts/addresses"""

        pidb = ParsedItemsDb()

        with ZipFile(path) as fzip:
            for fname in filter(lambda x: re.match(cls.ARCHIVE_PATHS, x), fzip.namelist()):
                for addr in file_from_zip(path, fname).decode('utf-8').splitlines():
                    pidb.upsert_host(addr)

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
