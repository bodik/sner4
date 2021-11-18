# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from ipaddress import ip_address
from pprint import pprint

from tenable.reports import NessusReportv2

from sner.server.parser import ParserBase, ParsedHost, ParsedItemsDb, ParsedService, ParsedVuln
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
            host = cls._parse_host(report_item)
            service = cls._parse_service(report_item, host.handle)
            vuln = cls._parse_vuln(report_item, host.handle, service.handle if service else None)

            pidb.hosts.upsert(host)
            if service:
                pidb.services.upsert(service)
            pidb.vulns.upsert(vuln)

        return pidb

    @classmethod
    def _parse_host(cls, report_item):
        """parse host data from report item"""

        host = ParsedHost(address=report_item['host-ip'])

        hostnames = []
        if 'host-fqdn' in report_item:
            hostnames.append(report_item['host-fqdn'])
        # host-rdns might contain address
        if ('host-rdns' in report_item) and (not cls.is_addr(report_item['host-rdns'])):
            hostnames.append(report_item['host-rdns'])
        hostnames = list(set(hostnames))

        if hostnames:
            host.hostnames = hostnames
            if not host.hostname:
                host.hostname = host.hostnames[0]

        if 'operating-system' in report_item:
            host.os = report_item['operating-system']

        return host

    @staticmethod
    def _parse_service(report_item, host_handle):
        """parse service data from report_item"""

        if report_item['port'] == 0:
            return None

        return ParsedService(
            host_handle=host_handle,
            proto=report_item['protocol'].lower(),
            port=report_item['port'],
            state='open:nessus',
            name=report_item['svc_name'],
            import_time=report_item['HOST_START']
        )

    @classmethod
    def _parse_vuln(cls, report_item, host_handle, service_handle=None):
        """parse vuln data"""

        vuln = ParsedVuln(
            host_handle=host_handle,
            service_handle=service_handle,
            via_target=report_item['host-report-name'],
            name=report_item['plugin_name'],
            xtype=f'nessus.{report_item["pluginID"]}',
            severity=SeverityEnum(cls.SEVERITY_MAP[report_item['severity']]),
            descr=f'## Synopsis\n\n{report_item["synopsis"]}\n\n## Description\n\n{report_item["description"]}',
            refs=cls._parse_refs(report_item),
            import_time=report_item['HOST_START'],
        )

        if 'plugin_output' in report_item:
            raw_data = json.dumps(report_item, cls=SnerJSONEncoder)
            vuln.data = f'## Plugin output\n\n{report_item["plugin_output"]}\n\n## Raw data\n\n{raw_data}'

        return vuln

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
