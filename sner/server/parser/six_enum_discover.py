# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import re
import sys
from zipfile import ZipFile

from sner.lib import file_from_zip
from sner.server.parser import ParserBase, register_parser


@register_parser('six_enum_discover')  # pylint: disable=too-few-public-methods
class SixEnumDiscoverParser(ParserBase):
    """six enum parser, pulls list of hosts for discovery module"""

    @staticmethod
    def host_list(path):
        """parse path and returns list of hosts/addresses"""

        result = []
        with ZipFile(path) as fzip:
            for ftmp in [fname for fname in fzip.namelist() if re.match(r'output\-[0-9]+\.txt', fname)]:
                result += file_from_zip(path, ftmp).decode('utf-8').splitlines()
        return result


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    print('## host list parser')
    print(SixEnumDiscoverParser.host_list(sys.argv[1]))


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
