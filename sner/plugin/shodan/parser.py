# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pathlib import Path
from pprint import pprint

from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nmap xml output parser"""

    NAMELEN = 100

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()
        return cls._parse_data(Path(path).read_text(encoding='utf-8'), pidb)

    @classmethod
    def _parse_data(cls, data, pidb):
        """parse raw string data"""

        data = list(map(json.loads, data.splitlines()))

        for ihost in data:
            # parse host
            host_data = {}
            if ihost['hostnames']:
                host_data['hostnames'] = list(set(ihost['hostnames']))
                if not host_data.get('hostname'):
                    host_data['hostname'] = host_data['hostnames'][0]

            pidb.upsert_host(ihost['ip_str'], **host_data)

            # parse services
            for iservice in ihost['data']:
                service_data = {
                    'state': 'open:shodan',
                    'import_time': iservice['timestamp']
                }
                pidb.upsert_service(ihost['ip_str'], iservice['transport'], iservice['port'], **service_data)

                for key, value in iservice.items():
                    if key in ['ip', 'ip_str', 'transport', 'timestamp', 'hash', '_shodan', 'port']:
                        continue
                    if not value:
                        continue
                    pidb.upsert_note(ihost['ip_str'], f'shodan.{key}', iservice['transport'], iservice['port'], data=json.dumps(value))

                for vulnid, vuln_data in iservice.get('vulns', {}).items():
                    pidb.upsert_vuln(
                        ihost['ip_str'],
                        f'{vulnid} {vuln_data["summary"][:cls.NAMELEN]}',
                        f'shodan.{vulnid}',
                        iservice['transport'],
                        iservice['port'],
                        descr=vuln_data['summary'],
                        data=json.dumps(vuln_data),
                        refs=[f'URL-{x}' for x in vuln_data['references']],
                        severity='unknown',
                    )

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]).__dict__)
