# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from sner.lib import file_from_zip
from sner.server.parser import ParsedHost, ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """dummy parser"""

    @classmethod
    def parse_path(cls, path):
        """parse path and returns list of hosts/addresses"""

        pidb = ParsedItemsDb()

        assignment = json.loads(file_from_zip(path, 'assignment.json'))
        for target in assignment['targets']:
            pidb.hosts.upsert(ParsedHost(address=target))

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
