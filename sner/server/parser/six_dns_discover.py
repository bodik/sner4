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
    def import_file(path):  # pragma: no cover  ; won't test
        """import nmap data from file or archive"""
        raise NotImplementedError

    @staticmethod
    def service_list(path):  # pragma: no cover  ; won't test
        """parse path and returns list of services in manymap target format"""
        raise NotImplementedError

    @staticmethod
    def host_list(path):
        """parse path and returns list of hosts/addresses"""

        data = json.loads(file_from_zip(path, 'output.json'))
        return list(data.keys())


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    print('## host list parser')
    print(SixDnsDiscoverParser.host_list(sys.argv[1]))


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
