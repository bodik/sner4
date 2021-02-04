# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent module manymap output to storage
"""

import sys
from pprint import pprint

from sner.plugin.nmap.parser import ParserModule as NmapParserModule


class ParserModule(NmapParserModule):  # pylint: disable=too-few-public-methods
    """inet endpoints scanner xml output parser; the module uses nmap hence parse uses nmap parser"""

    ARCHIVE_PATHS = r'output\-[0-9]+\.xml'


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
