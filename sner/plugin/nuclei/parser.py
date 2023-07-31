# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import logging
from zipfile import ZipFile
from pathlib import Path
from urllib.parse import urlsplit

from sner.lib import file_from_zip, is_zip
from sner.server.parser import ParsedItemsDb, ParserBase
from sner.server.storage.models import SeverityEnum
from sner.server.utils import SnerJSONEncoder
from sner.plugin.nessus.parser import ParserModule as NessusParser


logger = logging.getLogger(__name__)


def get_nested_key(data, *keys):
    """get nested key from dict"""

    try:
        for key in keys:
            data = data[key]
        return data
    except KeyError:
        return None


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nuclei output parser"""

    @classmethod
    def parse_path(cls, path):
        """parse data from path"""

        pidb = ParsedItemsDb()

        if is_zip(path):
            with ZipFile(path) as fzip:
                for fname in filter(lambda x: 'output.json' == x, fzip.namelist()):
                    pidb = cls._parse_data(file_from_zip(path, fname).decode('utf-8'), pidb)

            return pidb
        return cls._parse_data(Path(path).read_text(encoding='utf-8'), pidb)

    @classmethod
    def _parse_data(cls, data, pidb):  # pylint: disable=too-many-locals
        """parse taw string data"""

        data = json.loads(data)

        for report in data:
            if 'ip' not in report:
                # dns templates are skipped
                logger.warning('IP missing in report, %s', report["template"])
                continue

            # parse host
            host_address = report['ip']
            host_data = {}
            hostname = urlsplit(report['host']).hostname
            if not NessusParser.is_addr(hostname):
                host_data['hostname'] = hostname

            pidb.upsert_host(host_address, **host_data)

            # parse service
            service = None
            # url must contain '//' otherwise will be treated as relative and port will be parsed as path
            target_parsed = urlsplit(report['matched-at'] if '://' in report['matched-at'] else f"//{report['matched-at']}")
            port = target_parsed.port
            if (port is None) and (report['type'] == 'http'):
                # set default ports
                port = '443' if target_parsed.scheme == 'https' else '80'
            via_target = target_parsed.hostname

            if port:
                service = pidb.upsert_service(
                    host_address,
                    proto='tcp',
                    port=int(port),
                    state='open:nuclei',
                    name='www' if report['type'] == 'http' else '',
                    import_time=report['timestamp']
                )

            # parse vuln
            refs = []
            if cves := get_nested_key(report, 'info', 'classification', 'cve-id'):
                for cve in cves:
                    refs.append(cve.upper())
            if references := get_nested_key(report, 'info', 'reference'):
                for reference in references:
                    refs.append('URL-' + reference)

            vuln_data = {
                'via_target': via_target,
                'severity': str(SeverityEnum(report['info']['severity'])),
                'descr': f'## Description\n\n{report["info"].get("description")}\n\n'
                         + f'## Extracted results\n\n{report.get("extracted-results")}',
                'data': json.dumps(report, cls=SnerJSONEncoder),
                'refs': refs,
                'import_time': report['timestamp'],
            }
            if service:
                vuln_data['service_proto'] = service.proto
                vuln_data['service_port'] = service.port

            pidb.upsert_vuln(
                host_address,
                name=report['info']['name'],
                xtype=f"nuclei.{report['template-id']}",
                **vuln_data
            )

        return pidb
