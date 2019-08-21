# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pprint import pprint

from nessus_report_parser import parse_nessus_xml

from sner.server import db
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln
from sner.server.parser import ParserBase, register_parser
from sner.server.utils import SnerJSONEncoder


@register_parser('nessus')  # pylint: disable=too-few-public-methods
class NessusParser(ParserBase):
    """nessus .nessus output parser"""

    SEVERITY_MAP = {'0': 'info', '1': 'low', '2': 'medium', '3': 'high', '4': 'critical'}

    @staticmethod
    def import_file(path):
        """import nessus data from file"""

        with open(path, 'r') as ftmp:
            NessusParser._data_to_storage(ftmp.read())

    @staticmethod
    def _data_to_storage(data):
        """parse data and put/update models in storage"""

        report = parse_nessus_xml(data)['report']
        for ihost in report['hosts']:
            host = NessusParser._import_host(ihost)
            for ireport_item in ihost['report_items']:
                NessusParser._import_report_item(host, ireport_item)
            print('parsed host: %s' % host)

        db.session.commit()

    @staticmethod
    def _import_host(nessushost):
        """pull host to storage"""

        host = Host.query.filter(Host.address == nessushost['tags']['host-ip']).one_or_none()
        if not host:
            host = Host(address=nessushost['tags']['host-ip'])
            db.session.add(host)

        if 'host-fqdn' in nessushost['tags']:
            if not host.hostname:
                host.hostname = nessushost['tags']['host-fqdn']

            if host.hostname != nessushost['tags']['host-fqdn']:
                note = Note.query.filter(Note.host == host, Note.xtype == 'hostnames').one_or_none()
                if not note:
                    note = Note(host=host, xtype='hostnames', data=json.dumps([host.hostname]))
                    db.session.add(note)
                note.data = json.dumps(list(set(json.loads(note.data) + [nessushost['tags']['host-fqdn']])))

        if 'operating-system' in nessushost['tags']:
            host.os = nessushost['tags']['operating-system']

        return host

    @staticmethod
    def _import_report_item(host, report_item):
        """import nessus_v2 ReportItem 'element'"""

        port = int(report_item['port'])
        xtype = 'nessus.%s' % report_item['plugin_id']
        service = None

        if port:
            service = Service.query.filter(
                Service.host == host,
                Service.proto == report_item['protocol'],
                Service.port == port).one_or_none()
            if not service:
                service = Service(host=host, proto=report_item['protocol'], port=port)
                db.session.add(service)

            service.state = 'open:nessus'
            service.name = report_item['service_name']

        note = Note.query.filter(Note.host == host, Note.service == service, Note.xtype == xtype).one_or_none()
        if not note:
            note = Note(host=host, service=service, xtype=xtype)
            db.session.add(note)
        note.data = json.dumps(report_item, cls=SnerJSONEncoder)
        db.session.flush()  # required to get .id

        vuln = Vuln.query.filter(Vuln.host == host, Vuln.service == service, Vuln.xtype == xtype).one_or_none()
        if not vuln:
            vuln = Vuln(host=host, service=service, xtype=xtype)
            db.session.add(vuln)

        refs = ['SN-%s' % note.id]
        if 'cve' in report_item:
            refs += [ref for ref in report_item['cve']]
        if 'bid' in report_item:
            refs += ['BID-%s' % ref for ref in report_item['bid']]
        if 'xref' in report_item:
            refs += ['%s-%s' % tuple(ref.split(':', maxsplit=1)) for ref in report_item['xref']]
        if ('see_also' in report_item) and report_item['see_also']:
            refs += ['URL-%s' % ref for ref in report_item['see_also'].splitlines()]
        if ('metasploit_name' in report_item) and report_item['metasploit_name']:
            refs.append('MSF-%s' % report_item['metasploit_name'])
        if ('plugin_id' in report_item) and report_item['plugin_id']:
            refs.append('NSS-%s' % report_item['plugin_id'])

        vuln.name = report_item['plugin_name']
        vuln.severity = SeverityEnum(NessusParser.SEVERITY_MAP[report_item['severity']])
        vuln.descr = '## Synopsis\n\n%s\n\n ##Description\n\n%s' % (report_item['synopsis'], report_item['description'])
        vuln.data = report_item['plugin_output']
        vuln.refs = refs

        return vuln


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    with open(sys.argv[1], 'r') as ftmp:
        report = parse_nessus_xml(ftmp.read())['report']

    for host in report['hosts']:
        print('# host: %s' % host["name"])
        print('## host tags')
        pprint(host["tags"])
        print('## host report_items')
        for item in host["report_items"]:
            print('### item %s' % item['plugin_name'])
            pprint(item)


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
