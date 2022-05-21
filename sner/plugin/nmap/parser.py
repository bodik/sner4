# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint
from time import time
from zipfile import ZipFile

import libnmap.parser

from sner.lib import file_from_zip, is_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nmap xml output parser"""

    ARCHIVE_PATHS = r'output\.xml|output6\.xml'

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        if is_zip(path):
            with ZipFile(path) as fzip:
                for fname in filter(lambda x: re.match(cls.ARCHIVE_PATHS, x), fzip.namelist()):
                    pidb = cls._parse_data(file_from_zip(path, fname).decode('utf-8'), pidb)

            return pidb

        return cls._parse_data(Path(path).read_text(encoding='utf-8'), pidb)

    @classmethod
    def _parse_data(cls, data, pidb):
        """parse raw string data"""

        report = libnmap.parser.NmapParser.parse_fromstring(data)

        for ihost in report.hosts:
            # metadata
            via_target = ihost.user_target_hostname or ihost.address
            import_time = datetime.fromtimestamp(int(ihost.starttime or time()))

            # parse host
            host_data = {}
            if ihost.hostnames:
                host_data['hostnames'] = list(set(ihost.hostnames))
                if not host_data.get('hostname'):
                    host_data['hostname'] = host_data['hostnames'][0]

            for osmatch in [item for item in ihost.os_match_probabilities() if item.accuracy == 100]:
                host_data['os'] = osmatch.name
                pidb.upsert_note(ihost.address, 'cpe', data=json.dumps(osmatch.get_cpe()))

            pidb.upsert_host(ihost.address, **host_data)

            # parse host scripts
            for iscript in ihost.scripts_results:
                pidb.upsert_note(ihost.address, f'nmap.{iscript["id"]}', via_target=via_target, data=json.dumps(iscript), import_time=import_time)

            # parse services
            for iservice in ihost.services:
                service_data = {
                    'state': f'{iservice.state}:{iservice.reason}',
                    'import_time': import_time
                }
                if iservice.service:
                    service_data['name'] = iservice.service
                if iservice.banner:
                    service_data['info'] = iservice.banner
                pidb.upsert_service(ihost.address, iservice.protocol, iservice.port, **service_data)

                if iservice.cpelist:
                    pidb.upsert_note(
                        ihost.address,
                        'cpe',
                        iservice.protocol,
                        iservice.port,
                        via_target,
                        data=json.dumps([x.cpestring for x in iservice.cpelist]),
                        import_time=import_time
                    )

                # parse service scripts
                for iscript in iservice.scripts_results:
                    pidb.upsert_note(
                        ihost.address,
                        f'nmap.{iscript["id"]}',
                        iservice.protocol,
                        iservice.port,
                        via_target,
                        data=json.dumps(iscript),
                        import_time=import_time
                    )

        return pidb


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]).__dict__)
