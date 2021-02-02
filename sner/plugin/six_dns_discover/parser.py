# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from sner.lib import file_from_zip
from sner.server.parser import ParsedHost, ParsedItemsDb, ParsedNote, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """six dns parser, pulls list of hosts for discovery module"""

    @staticmethod
    def parse_path(path):
        """parse data from path"""

        pidb = ParsedItemsDb()
        data = json.loads(file_from_zip(path, 'output.json'))

        for addr, via in data.items():
            host = ParsedHost(address=addr)
            note = ParsedNote(host_handle=host.handle, xtype='six_dns_discover.via', data=json.dumps(via))
            pidb.hosts.upsert(host)
            pidb.notes.upsert(note)

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
