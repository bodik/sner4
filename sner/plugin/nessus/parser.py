# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from tenable.reports import NessusReportv2

from sner.server.parser import ParserBase, ParsedHost, ParsedItemsDict as Pdict, ParsedNote, ParsedService, ParsedVuln
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

        hosts, services, vulns, notes = Pdict(), Pdict(), Pdict(), Pdict()

        for report_item in report:
            host = cls._parse_host(report_item)
            service = cls._parse_service(report_item)
            vuln = cls._parse_vuln(report_item, service)
            note = cls._parse_note(report_item, service)

            for storage, item in [(hosts, host), (services, service), (vulns, vuln), (notes, note)]:
                if item:
                    storage.upsert(item)

        return list(hosts.values()), list(services.values()), list(vulns.values()), list(notes.values())

    @staticmethod
    def _parse_host(report_item):
        """parse host data from report item"""

        host = ParsedHost(
            handle={'host': report_item['host-ip']},
            address=report_item['host-ip']
        )

        hostnames = list(set(filter(lambda x: x, [report_item.get('host-fqdn'), report_item.get('host-rdns')])))
        if hostnames:
            host.hostnames = hostnames
            if not host.hostname:
                host.hostname = host.hostnames[0]

        if 'operating-system' in report_item:
            host.os = report_item['operating-system']

        return host

    @staticmethod
    def _parse_service(report_item):
        """parse service data from report_item"""

        if report_item['port'] == 0:
            return None

        return ParsedService(
            handle={'host': report_item['host-ip'], 'service': f'{report_item["protocol"]}/{report_item["port"]}'},
            proto=report_item['protocol'],
            port=report_item['port'],
            state='open:nessus',
            name=report_item['svc_name'],
            import_time=report_item['HOST_START']
        )

    @classmethod
    def _parse_vuln(cls, report_item, service=None):
        """parse vuln data"""

        handle = {'host': report_item['host-ip'], 'vuln': f'nessus.{report_item["pluginID"]}'}
        if service:
            handle['service'] = f'{report_item["protocol"]}/{report_item["port"]}'

        vuln = ParsedVuln(
            handle=handle,
            name=report_item['plugin_name'],
            xtype=f'nessus.{report_item["pluginID"]}',
            severity=SeverityEnum(cls.SEVERITY_MAP[report_item['severity']]),
            descr=f'## Synopsis\n\n{report_item["synopsis"]}\n\n## Description\n\n{report_item["description"]}',
            refs=cls._parse_refs(report_item),
            import_time=report_item['HOST_START'],
        )

        if 'plugin_output' in report_item:
            vuln.data = report_item['plugin_output']

        return vuln

    @staticmethod
    def _parse_note(report_item, service=None):
        """parse notes data"""

        handle = {'host': report_item['host-ip'], 'vuln': f'nessus.{report_item["pluginID"]}', 'note': f'nessus.{report_item["pluginID"]}'}
        if service:
            handle['service'] = f'{report_item["protocol"]}/{report_item["port"]}'

        return ParsedNote(
            handle=handle,
            xtype=f'nessus.{report_item["pluginID"]}',
            data=json.dumps(report_item, cls=SnerJSONEncoder),
            import_time=report_item['HOST_START']
        )

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
            refs += ['%s-%s' % tuple(ref.split(':', maxsplit=1)) for ref in ensure_list(report_item['xref'])]
        if 'see_also' in report_item:
            refs += [f'URL-{ref}' for ref in report_item['see_also'].splitlines()]
        if 'metasploit_name' in report_item:
            refs.append(f'MSF-{report_item["metasploit_name"]}')
        if 'pluginID' in report_item:
            refs.append(f'NSS-{report_item["pluginID"]}')

        return refs


if __name__ == '__main__':  # pragma: no cover
    pprint(ParserModule.parse_path(sys.argv[1]))
