# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent module manymap output to storage
"""

import re
import sys
from pathlib import Path
from pprint import pprint
from zipfile import ZipFile

from sner.lib import is_zip, file_from_zip
from sner.server.parser import register_parser
from sner.server.parser.core import ParsedItemsDict as Pdict
from sner.server.parser.nmap import NmapParser


@register_parser('manymap')  # pylint: disable=too-few-public-methods
class ManymapParser(NmapParser):
    """inet endpoints scanner xml output parser; the module uses nmap hence parse uses nmap parser"""

    @staticmethod
    def parse_path(path):
        """import file from disk to storage"""

        if is_zip(path):
            hosts, services, vulns, notes = Pdict(), Pdict(), Pdict(), Pdict()
            with ZipFile(path) as fzip:
                for ftmp in [fname for fname in fzip.namelist() if re.match(r'output\-[0-9]+\.xml', fname)]:

                    thosts, tservices, tvulns, tnotes = NmapParser._parse_data(file_from_zip(path, ftmp).decode('utf-8'))
                    for storage, items in [(hosts, thosts), (services, tservices), (vulns, tvulns), (notes, tnotes)]:
                        for item in items:
                            storage.upsert(item)

            return list(hosts.values()), list(services.values()), list(vulns.values()), list(notes.values())

        return NmapParser._parse_data(Path(path).read_text())


if __name__ == '__main__':  # pragma: no cover
    pprint(ManymapParser.parse_path(sys.argv[1]))
