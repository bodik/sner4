# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from ipaddress import ip_address
from pprint import pprint

from tenable.reports import NessusReportv2

from sner.server.parser import ParsedItemsDb, ParserBase
from sner.server.storage.models import SeverityEnum
from sner.server.utils import SnerJSONEncoder


class ParserModule(ParserBase):  # pylint: disable=too-few-public-methods
    """nessus .nessus output parser"""

    SEVERITY_MAP = ['info', 'low', 'medium', 'high', 'critical']

    @classmethod
    def parse_path(cls, path):
        """parse path"""

        return cls._parse_report(NessusReportv2(path))

    @classmethod
    def _parse_report(cls, report):
        """parses host data from report item"""

        pidb = ParsedItemsDb()

        for report_item in report:
            # parse host
            host_address = report_item['host-ip']
            host_data = {}

            hostnames = set()
            if 'host-fqdn' in report_item:
                hostnames.add(report_item['host-fqdn'])
            # host-rdns might contain address
            if ('host-rdns' in report_item) and (not cls.is_addr(report_item['host-rdns'])):
                hostnames.add(report_item['host-rdns'])
            if hostnames:
                host_data['hostnames'] = list(hostnames)
                host_data['hostname'] = host_data['hostnames'][0]

            if 'operating-system' in report_item:
                host_data['os'] = report_item['operating-system']

            pidb.upsert_host(host_address, **host_data)

            # parse service
            service = None
            if report_item['port'] != 0:
                service = pidb.upsert_service(
                    host_address,
                    report_item['protocol'].lower(),
                    report_item['port'],
                    state='open:nessus',
                    name=report_item['svc_name'],
                    import_time=report_item['HOST_START']
                )

            # parse vuln
            vuln_data = {
                'severity': SeverityEnum(cls.SEVERITY_MAP[report_item['severity']]),
                'descr': f'## Synopsis\n\n{report_item["synopsis"]}\n\n## Description\n\n{report_item["description"]}',
                'refs': cls._parse_refs(report_item),
                'import_time': report_item['HOST_START'],
            }
            if service:
                vuln_data['service_proto'] = service.proto
                vuln_data['service_port'] = service.port

            if 'plugin_output' in report_item:
                raw_data = json.dumps(report_item, cls=SnerJSONEncoder)
                vuln_data['data'] = f'## Plugin output\n\n{report_item["plugin_output"]}\n\n## Raw data\n\n{raw_data}'

            pidb.upsert_vuln(
                host_address,
                report_item['plugin_name'],
                f'nessus.{report_item["pluginID"]}',
                via_target=report_item['host-report-name'],
                **vuln_data
            )

        return pidb

    @staticmethod
    def _parse_refs(report_item):
        """compile refs array for report_item"""

        def ensure_list(data):
            return [data] if isinstance(data, str) else data

        refs = []
        if 'cve' in report_item:
            refs += ensure_list(report_item['cve'])
        if 'bid' in report_item:
            refs += [f'BID-{ref}' for ref in ensure_list(report_item['bid'])]
        if 'xref' in report_item:
            refs += ['%s-%s' % tuple(ref.split(':', maxsplit=1)) for ref in ensure_list(report_item['xref'])]  # noqa: E501  pylint: disable=consider-using-f-string
        if 'see_also' in report_item:
            refs += [f'URL-{ref}' for ref in report_item['see_also'].splitlines()]
        if 'metasploit_name' in report_item:
            refs.append(f'MSF-{report_item["metasploit_name"]}')
        if 'pluginID' in report_item:
            refs.append(f'NSS-{report_item["pluginID"]}')

        return refs

    @staticmethod
    def is_addr(addr):
        """check if argument is internet address"""

        try:
            ip_address(addr)
            return True
        except ValueError:
            return False


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
