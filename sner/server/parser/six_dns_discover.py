# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys

from sner.lib import file_from_zip
from sner.server.parser import ParserBase, register_parser


@register_parser('six_dns_discover')  # pylint: disable=too-few-public-methods
class SixDnsDiscoverParser(ParserBase):
    """six dns parser, pulls list of hosts for discovery module"""

    @staticmethod
    def host_list(path):
        """parse host list from path"""

        data = json.loads(file_from_zip(path, 'output.json'))
        return list(data.keys())


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    print('## host list parser')
    print(SixDnsDiscoverParser.host_list(sys.argv[1]))


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
