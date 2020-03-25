# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from tenable.reports import NessusReportv2

from sner.server.extensions import db
from sner.server.parser import ParserBase, register_parser
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln
from sner.server.utils import SnerJSONEncoder


@register_parser('nessus')  # pylint: disable=too-few-public-methods
class NessusParser(ParserBase):
    """nessus .nessus output parser"""

    SEVERITY_MAP = ['info', 'low', 'medium', 'high', 'critical']

    @staticmethod
    def import_file(path):
        """import nessus data from file"""

        with open(path, 'r') as ftmp:
            for item in NessusReportv2(ftmp):
                tmp = NessusParser._import_report_item(item)
                print('parsed item: %s %s' % (tmp.host, tmp))
        db.session.commit()

    @staticmethod
    def _import_report_item(report_item):
        """import nessus_v2 ReportItem 'element'"""

        xtype = 'nessus.%s' % report_item['pluginID']
        host = NessusParser._import_host(report_item)
        service = NessusParser._import_service(report_item, host)
        note = NessusParser._import_vuln_note(report_item, host, service, xtype)

        vuln = Vuln.query.filter(Vuln.host == host, Vuln.service == service, Vuln.xtype == xtype).one_or_none()
        if not vuln:
            vuln = Vuln(host=host, service=service, xtype=xtype)
            db.session.add(vuln)
        vuln.name = report_item['plugin_name']
        vuln.severity = SeverityEnum(NessusParser.SEVERITY_MAP[report_item['severity']])
        vuln.descr = '## Synopsis\n\n%s\n\n## Description\n\n%s' % (report_item['synopsis'], report_item['description'])
        if 'plugin_output' in report_item:
            vuln.data = report_item['plugin_output']
        vuln.refs = ['SN-%s' % note.id] + NessusParser._get_refs(report_item)

        return vuln

    @staticmethod
    def _import_host(report_item):
        """pull host to storage"""

        def upsert_hostname(host, hostname):
            """upsert hostname to host model"""

            if hostname != host.hostname:
                note = Note.query.filter(Note.host == host, Note.xtype == 'hostnames').one_or_none()
                if not note:
                    note = Note(host=host, xtype='hostnames', data=json.dumps([host.hostname]))
                    db.session.add(note)
                note.data = json.dumps(list(set(json.loads(note.data) + [hostname])))

        host = Host.query.filter(Host.address == report_item['host-ip']).one_or_none()
        if not host:
            host = Host(address=report_item['host-ip'])
            db.session.add(host)
        if 'host-fqdn' in report_item:
            if not host.hostname:
                host.hostname = report_item['host-fqdn']
            upsert_hostname(host, report_item['host-fqdn'])
        if 'host-rdns' in report_item:
            upsert_hostname(host, report_item['host-rdns'])
        if 'operating-system' in report_item:
            host.os = report_item['operating-system']

        return host

    @staticmethod
    def _import_service(report_item, host):
        """pull service to storage"""

        if report_item['port'] == 0:
            return None

        service = Service.query.filter(
            Service.host == host,
            Service.proto == report_item['protocol'],
            Service.port == report_item['port']).one_or_none()
        if not service:
            service = Service(host=host, proto=report_item['protocol'], port=report_item['port'])
            db.session.add(service)
        service.state = 'open:nessus'
        service.name = report_item['svc_name']

        return service

    @staticmethod
    def _import_vuln_note(report_item, host, service, xtype):
        """put vulnerability note to storage"""

        note = Note.query.filter(Note.host == host, Note.service == service, Note.xtype == xtype).one_or_none()
        if not note:
            note = Note(host=host, service=service, xtype=xtype)
            db.session.add(note)
        note.data = json.dumps(report_item, cls=SnerJSONEncoder)
        db.session.flush()  # required to get .id

        return note

    @staticmethod
    def _get_refs(report_item):
        """compile refs array for report_item"""

        def ensure_list(data):
            return [data] if isinstance(data, str) else data

        refs = []
        if 'cve' in report_item:
            refs += ensure_list(report_item['cve'])
        if 'bid' in report_item:
            refs += ['BID-%s' % ref for ref in ensure_list(report_item['bid'])]
        if 'xref' in report_item:
            refs += ['%s-%s' % tuple(ref.split(':', maxsplit=1)) for ref in ensure_list(report_item['xref'])]
        if 'see_also' in report_item:
            refs += ['URL-%s' % ref for ref in report_item['see_also'].splitlines()]
        if 'metasploit_name' in report_item:
            refs.append('MSF-%s' % report_item['metasploit_name'])
        if 'pluginID' in report_item:
            refs.append('NSS-%s' % report_item['pluginID'])

        return refs


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    with open(sys.argv[1], 'r') as ftmp:
        report = NessusReportv2(ftmp)
        for item in report:
            pprint(item)


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
