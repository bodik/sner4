# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys

import libnmap.parser

from sner.server import db
from sner.server.parser import register_parser
from sner.server.model.storage import Host, Note, Service


@register_parser('nmap')
class NmapParser():
    """nmap xml output parser"""

    JOB_OUTPUT_DATAFILE = 'output.xml'

    @staticmethod
    def import_host(nmaphost):
        """pull host to storage"""

        host = Host.query.filter(Host.address == nmaphost.address).one_or_none()
        if not host:
            host = Host(address=nmaphost.address)
            db.session.add(host)

        if (not host.hostname) and nmaphost.hostnames:
            host.hostname = nmaphost.hostnames[0]

        for osmatch in nmaphost.os_match_probabilities():
            if (osmatch.accuracy == 100) and (not host.os):
                host.os = osmatch.name

        for iscript in nmaphost.scripts_results:
            xtype = 'nmap.%s' % iscript["id"]
            note = Note.query.filter(Note.host == host, Note.xtype == xtype).one_or_none()
            if not note:
                note = Note(host=host, xtype=xtype, data=json.dumps(iscript))
                db.session.add(note)

        return host

    @staticmethod
    def import_service(host, nmapservice):
        """pull service to storage"""

        service = Service.query.filter(Service.host == host, Service.proto == nmapservice.protocol, Service.port == nmapservice.port).one_or_none()
        if not service:
            service = Service(host=host, proto=nmapservice.protocol, port=nmapservice.port)
            db.session.add(service)

        if not service.state:
            service.state = "%s:%s" % (nmapservice.state, nmapservice.reason)
        if not service.name:
            service.name = nmapservice.service
        if not service.info:
            service.info = nmapservice.banner

        for iscript in nmapservice.scripts_results:
            xtype = 'nmap.%s' % iscript["id"]
            note = Note.query.filter(Note.host == host, Note.service == service, Note.xtype == xtype).one_or_none()
            if not note:
                note = Note(host=host, service=service, xtype=xtype, data=json.dumps(iscript))
                db.session.add(note)

        return service

    @staticmethod
    def data_to_storage(data):
        """parse data and put/update models in storage"""

        report = libnmap.parser.NmapParser.parse_fromstring(data)
        for ihost in report.hosts:
            host = NmapParser.import_host(ihost)

            for iservice in ihost.services:
                NmapParser.import_service(host, iservice)

            print('parsed host: %s' % host)
        db.session.commit()


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    with open(sys.argv[1], 'r') as ftmp:
        report = libnmap.parser.NmapParser.parse_fromstring(ftmp.read())

    for host in report.hosts:
        print('# host: %s' % host.hostnames)
        print('## host dict')
        print(host.get_dict())
        print('## host os_match_probabilities')
        for tmp in host.os_match_probabilities():
            print("- %s %s" % (tmp.accuracy, tmp.name))
        print('## host scripts_results')
        print(host.scripts_results)
        print('## host services')
        for tmp in host.services:
            print('### service')
            print(tmp.get_dict())
            print('#### service scripts_results')
            print(json.dumps(tmp.scripts_results, indent=2))


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
