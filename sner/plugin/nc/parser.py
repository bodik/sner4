# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nc/netcat zero-I/O mode scanner parser. Should support nc and OpenBSD nc variant.

```
nc -zv localhost 22 1>scan.txt 2>&1
bin/server storage import nc scan.txt
```
"""

import logging
import re
import sys
from pathlib import Path
from pprint import pprint

from sner.server.parser import ParsedHost, ParsedItemsDb, ParsedService, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nc output parser"""

    REGEX = r'^\(?(?P<hostname>.*)\)? \[(?P<address>[0-9a-f\.:]+)\] (?P<port>[0-9]+) \(.*\):? (?P<result>.*)$'
    REGEX_OPENBSD = r'^(Connection to (?P<address>[0-9a-f\.:]+) (?P<port>[0-9]+) port \[.*\] (?P<result>.*))|(nc: connect to .* port .* \(.*\) .*)$'

    @staticmethod
    def parse_path(path):
        """parse data from path"""

        def upsert(pidb, data):
            host = ParsedHost(address=data['address'])
            service = ParsedService(host_handle=host.handle, proto='tcp', port=data['port'], state='open:nc')
            pidb.hosts.upsert(host)
            pidb.services.upsert(service)
            return pidb

        pidb = ParsedItemsDb()
        rex1 = re.compile(ParserModule.REGEX)
        rex2 = re.compile(ParserModule.REGEX_OPENBSD)

        for line in Path(path).read_text().splitlines():

            match = rex1.match(line)
            if match:
                if match.group('result') == 'open':
                    pidb = upsert(pidb, match.groupdict())
                continue

            match = rex2.match(line)
            if match:
                if match.group('result') == 'succeeded!':
                    pidb = upsert(pidb, match.groupdict())
                continue

            logging.warning('skipped line: "%s"', line)

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))