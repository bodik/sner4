# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
parsers to import from agent outputs to storage
"""

import json
import sys
from pathlib import Path

import libnmap.parser

from sner.lib import format_host_address, file_from_zip, is_zip
from sner.server.extensions import db
from sner.server.parser import ParserBase, register_parser
from sner.server.storage.models import Host, Note, Service


@register_parser('nmap')  # pylint: disable=too-few-public-methods
class NmapParser(ParserBase):
    """nmap xml output parser"""

    @staticmethod
    def import_file(path):
        """import nmap data from file or archive"""

        NmapParser._data_to_storage(NmapParser._rawdata_from_path(path))

    @staticmethod
    def service_list(path):
        """parse path and returns list of services in manymap target format"""

        services = []
        report = libnmap.parser.NmapParser.parse_fromstring(NmapParser._rawdata_from_path(path))
        for ihost in report.hosts:
            for iservice in ihost.services:
                services.append('%s://%s:%d' % (iservice.protocol, format_host_address(ihost.address), iservice.port))

        return services

    @staticmethod
    def _rawdata_from_path(path):
        """get path contents or output.xml from archive"""

        if is_zip(path):
            return file_from_zip(path, 'output.xml').decode('utf-8')
        return Path(path).read_text()

    @staticmethod
    def _data_to_storage(data):
        """parse data and put/update models in storage"""

        report = libnmap.parser.NmapParser.parse_fromstring(data)
        for ihost in report.hosts:
            host = NmapParser._import_host(ihost)

            for iservice in ihost.services:
                NmapParser._import_service(host, iservice)

            print('parsed host: %s' % host)
        db.session.commit()

    @staticmethod
    def _import_host(nmaphost):
        """pull host to storage"""

        host = Host.query.filter(Host.address == nmaphost.address).one_or_none()
        if not host:
            host = Host(address=nmaphost.address)
            db.session.add(host)

        if nmaphost.hostnames:
            hostnames = list(set(nmaphost.hostnames))

            if not host.hostname:
                host.hostname = hostnames[0]

            if (host.hostname != hostnames[0]) or (len(hostnames) > 1):
                note = Note.query.filter(Note.host == host, Note.xtype == 'hostnames').one_or_none()
                if not note:
                    note = Note(host=host, xtype='hostnames', data=json.dumps([host.hostname]))
                    db.session.add(note)
                note.data = json.dumps(list(set(json.loads(note.data) + hostnames)))

        for osmatch in nmaphost.os_match_probabilities():
            if osmatch.accuracy == 100:
                host.os = osmatch.name

        for iscript in nmaphost.scripts_results:
            xtype = 'nmap.%s' % iscript["id"]
            note = Note.query.filter(Note.host == host, Note.xtype == xtype).one_or_none()
            if not note:
                note = Note(host=host, xtype=xtype)
                db.session.add(note)
            note.data = json.dumps(iscript)

        return host

    @staticmethod
    def _import_service(host, nmapservice):
        """pull service to storage"""

        service = Service.query.filter(Service.host == host, Service.proto == nmapservice.protocol, Service.port == nmapservice.port).one_or_none()
        if not service:
            service = Service(host=host, proto=nmapservice.protocol, port=nmapservice.port)
            db.session.add(service)

        service.state = "%s:%s" % (nmapservice.state, nmapservice.reason)
        service.name = nmapservice.service if nmapservice.service else None
        service.info = nmapservice.banner if nmapservice.banner else None

        for iscript in nmapservice.scripts_results:
            xtype = 'nmap.%s' % iscript["id"]
            note = Note.query.filter(Note.host == host, Note.service == service, Note.xtype == xtype).one_or_none()
            if not note:
                note = Note(host=host, service=service, xtype=xtype)
                db.session.add(note)
            note.data = json.dumps(iscript)

        return service


def debug_parser():  # pragma: no cover
    """cli helper, pull data from report and display"""

    data = NmapParser._rawdata_from_path(sys.argv[1])  # pylint: disable=protected-access
    report = libnmap.parser.NmapParser.parse_fromstring(data)

    print('## default parser')
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

    print('## service list parser')
    print(NmapParser.service_list(sys.argv[1]))


if __name__ == '__main__':  # pragma: no cover
    debug_parser()
