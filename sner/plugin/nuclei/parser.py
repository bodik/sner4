# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import re
from zipfile import ZipFile
from pathlib import Path
from urllib.parse import urlsplit

from sner.lib import file_from_zip, is_zip
from sner.server.parser import ParsedItemsDb, ParserBase


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nuclei output parser"""

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        if is_zip(path):
            with ZipFile(path) as fzip:
                for fname in filter(lambda x: 'output.json' == x, fzip.namelist()):
                    pidb = cls._parse_data(file_from_zip(path, fname).decode('utf-8'), pidb)  # pragma: no cover

            return pidb
        return cls._parse_data(Path(path).read_text(encoding='utf-8'), pidb)

    @classmethod
    def _parse_data(cls, data, pidb):
        """parse taw string data"""

        data = json.loads(data)

        for report in data:
            if 'ip' not in report:  # pragma: no cover
                continue

            # parse host
            host_address = report['ip']
            hostname = urlsplit(report['host']).hostname

            pidb.upsert_host(host_address, **{'hostname': hostname})

            # parse service
            service = None
            port = re.search('(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*', report['matched-at']).group('port')

            if port == '':
                # set default ports
                if report['type'] == 'http':
                    port = '443' if urlsplit(report['matched-at']).scheme == 'https' else '80'

            if port:
                service = pidb.upsert_service(
                    host_address,
                    'tcp',
                    int(port),
                    state='open:nuclei',
                    name='www' if report['type'] == 'http' else '',
                    import_time=report['timestamp']
                )

            # parse vuln
            refs = []

            if 'classification' in report['info']:
                cves = report['info']['classification']['cve-id']
                if cves is not None:
                    for cve in cves:
                        refs.append(cve.upper())

            if 'reference' in report['info']:
                references = report['info']['reference']
                if references is not None:
                    for reference in references:
                        refs.append('URL-' + reference)

            vuln_data = {
                'severity': report['info']['severity'],
                'descr': report['info']['description'] if 'description' in report['info'] else '',
                'refs': refs
            }

            if service:
                vuln_data['service_proto'] = service.proto
                vuln_data['service_port'] = service.port

            pidb.upsert_vuln(
                host_address,
                report['info']['name'],
                report['template-id'],
                **vuln_data
            )

        return pidb
