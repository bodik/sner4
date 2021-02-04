# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from sner.lib import file_from_zip
from sner.server.parser import ParserBase, ParsedHost, ParsedNote


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """six dns parser, pulls list of hosts for discovery module"""

    @staticmethod
    def parse_path(path):
        """parse data from path"""

        hosts, notes = [], []
        data = json.loads(file_from_zip(path, 'output.json'))

        for addr, via in data.items():
            hosts.append(ParsedHost(handle={'host': addr}, address=addr))
            notes.append(ParsedNote(handle={'host': addr}, xtype='six_dns_discover.via', data=json.dumps(via)))

        return hosts, [], [], notes


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
