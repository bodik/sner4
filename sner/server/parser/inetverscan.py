# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent module inetverscan output to storage
"""

import re
from zipfile import ZipFile

from sner.lib import is_zip, file_from_zip
from sner.server.parser import register_parser
from sner.server.parser.nmap import NmapParser


@register_parser('inetverscan')  # pylint: disable=too-few-public-methods
class InetverscanParser(NmapParser):
    """inet endpoint version scanner xml output parser; the module uses nmap hence parse uses nmap parser"""

    @staticmethod
    def import_file(path):
        """import nmap data from file or achive"""

        if is_zip(path):
            with ZipFile(path) as fzip:
                for ftmp in [fname for fname in fzip.namelist() if re.match(r'output\-[0-9]+\.xml', fname)]:
                    NmapParser._data_to_storage(file_from_zip(path, ftmp).decode('utf-8'))
        else:
            with open(path, 'r') as ftmp:
                InetverscanParser._data_to_storage(ftmp.read())
