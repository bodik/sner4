# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage commands tests
"""

import json
import re

from sner.server import db
from sner.server.command.storage import storage_command
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln
from tests import persist_and_detach


def test_import_invalidparser(runner):
    """test invalid parser"""

    result = runner.invoke(storage_command, ['import', 'invalid', '/nonexistent'])
    assert result.exit_code == 1


def test_import_job_output(runner):
    """test import from job output parser"""

    result = runner.invoke(storage_command, ['import', 'nmap', 'tests/server/data/parser-nmap-job.zip'])
    assert result.exit_code == 0

    host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
    host = Host.query.filter(Host.id == host_id).one_or_none()
    assert host


def test_import_nmap_command(runner):
    """test nmap parser"""

    result = runner.invoke(storage_command, ['import', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0

    host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
    host = Host.query.filter(Host.id == host_id).one_or_none()
    assert host
    assert host.os == 'Linux 3.8 - 4.6'
    assert sorted([x.port for x in host.services]) == [22, 25, 139, 445, 5432]
    tmpnote = Note.query.join(Service).filter(Note.host == host, Service.port == 25, Note.xtype == 'nmap.smtp-commands').one_or_none()
    assert 'PIPELINING' in json.loads(tmpnote.data)['output']


def test_import_nessus_command(runner):
    """test nessus parser"""

    result = runner.invoke(storage_command, ['import', 'nessus', 'tests/server/data/parser-nessus-simple.xml'])
    assert result.exit_code == 0

    host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
    host = Host.query.filter(Host.id == host_id).one_or_none()
    assert host
    assert host.os == 'Microsoft Windows Vista'
    assert sorted([x.port for x in host.services]) == [443]
    tmpvuln = Vuln.query.join(Service).filter(Vuln.host == host, Service.port == 443, Vuln.xtype == 'nessus.104631').one_or_none()
    assert tmpvuln
    assert 'CVE-1900-0000' in tmpvuln.refs


def test_import_inetverscan_command_zipfile(runner):
    """test inetverscan parser; zipfile import"""

    result = runner.invoke(storage_command, ['import', 'inetverscan', 'tests/server/data/parser-inetverscan-job.zip'])
    assert result.exit_code == 0

    host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
    host = Host.query.filter(Host.id == host_id).one_or_none()
    assert host
    assert host.services[0].port == 18000
    assert host.services[0].info == 'product: Werkzeug httpd version: 0.15.5 extrainfo: Python 3.7.3'


def test_import_inetverscan_command_plaintext(runner):
    """test inetverscan parser; plaintext import"""

    result = runner.invoke(storage_command, ['import', 'inetverscan', 'tests/server/data/parser-inetverscan-output-1.xml'])
    assert result.exit_code == 0

    host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
    host = Host.query.filter(Host.id == host_id).one_or_none()
    assert host


def test_flush_command(runner, test_service, test_vuln, test_note):
    """flush storage database"""

    result = runner.invoke(storage_command, ['flush'])
    assert result.exit_code == 0

    assert not Host.query.all()
    assert not Service.query.all()
    assert not Vuln.query.all()
    assert not Note.query.all()


def test_report_command(runner, test_vuln):
    """test vuln report command"""

    db.session.add(Host(address='127.3.3.1', hostname='testhost2.testdomain.tests'))
    db.session.add(Host(address='127.3.3.2', hostname='testhost2.testdomain.tests'))
    db.session.add(Vuln(
        host=Host.query.filter(Host.address == '127.3.3.1').one_or_none(), name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical))
    db.session.add(Vuln(
        host=Host.query.filter(Host.address == '127.3.3.2').one_or_none(), name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical))
    db.session.commit()

    result = runner.invoke(storage_command, ['report'])
    assert result.exit_code == 0
    assert ',"%s",' % test_vuln.name in result.output


def test_host_cleanup_command(runner):
    """test host_cleanup command"""

    test_host1 = persist_and_detach(Host(address='127.127.127.135', os='identified'))
    test_host2 = persist_and_detach(Host(address='127.127.127.134'))
    persist_and_detach(Service(host_id=test_host2.id, proto='tcp', port=1, state='anystate:reason'))
    test_host3 = persist_and_detach(Host(address='127.127.127.133', hostname='xxx', os=''))

    result = runner.invoke(storage_command, ['host_cleanup', '--dry'])
    assert result.exit_code == 0

    assert repr(test_host1) not in result.output
    assert repr(test_host2) not in result.output
    assert repr(test_host3) in result.output
    assert Host.query.count() == 3

    result = runner.invoke(storage_command, ['host_cleanup'])
    assert result.exit_code == 0

    hosts = Host.query.all()
    assert len(hosts) == 2
    assert test_host3.id not in [x.id for x in hosts]


def test_service_list_command(runner, test_service):
    """test services listing"""

    host = Host.query.filter(Host.id == test_service.host_id).one()

    result = runner.invoke(storage_command, ['service_list', '--long', '--iponly'])
    assert result.exit_code == 1

    result = runner.invoke(storage_command, ['service_list'])
    assert result.exit_code == 0
    assert '%s://%s:%d\n' % (test_service.proto, host.address, test_service.port) == result.output

    result = runner.invoke(storage_command, ['service_list', '--long'])
    assert result.exit_code == 0
    assert json.dumps(test_service.info) in result.output

    result = runner.invoke(storage_command, ['service_list', '--iponly'])
    assert result.exit_code == 0
    assert len(result.output.splitlines()) == 1
    assert host.address in result.output

    result = runner.invoke(storage_command, ['service_list', '--filter', 'Service.port=="%d"' % test_service.port])
    assert result.exit_code == 0
    assert '%s://%s:%d\n' % (test_service.proto, host.address, test_service.port) == result.output


def test_service_cleanup_command(runner, test_host):
    """test service_cleanup command"""

    test_service1 = persist_and_detach(Service(host_id=test_host.id, proto='tcp', port=1, state='open:reason'))
    test_service2 = persist_and_detach(Service(host_id=test_host.id, proto='tcp', port=1, state='filtered:reason'))
    persist_and_detach(Note(host_id=test_host.id, service_id=test_service2.id, xtype='cleanuptest', data='atestdata'))

    result = runner.invoke(storage_command, ['service_cleanup', '--dry'])
    assert result.exit_code == 0

    assert repr(test_service1) not in result.output
    assert repr(test_service2) in result.output
    assert Service.query.count() == 2

    result = runner.invoke(storage_command, ['service_cleanup'])
    assert result.exit_code == 0

    assert Note.query.count() == 0
    services = Service.query.all()
    assert len(services) == 1
    assert services[0].id == test_service1.id
