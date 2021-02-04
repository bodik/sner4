# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import re
import sys
from pprint import pprint
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParserBase, ParsedHost


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """six enum parser, pulls list of hosts for discovery module"""

    @staticmethod
    def parse_path(path):
        """parse path and returns list of hosts/addresses"""

        hosts = []

        with ZipFile(path) as fzip:
            for ftmp in [fname for fname in fzip.namelist() if re.match(r'output\-[0-9]+\.txt', fname)]:
                for addr in file_from_zip(path, ftmp).decode('utf-8').splitlines():
                    hosts.append(ParsedHost(handle={'host': addr}, address=addr))

        return hosts, [], [], []


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
