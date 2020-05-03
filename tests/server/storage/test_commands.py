# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import json

from sner.server.storage.commands import command
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_import_invalidparser(runner):
    """test invalid parser"""

    result = runner.invoke(command, ['import', 'invalid', '/nonexistent'])
    assert result.exit_code == 1


def test_import_job_output(runner):
    """test import from job output parser"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-job.zip'])
    assert result.exit_code == 0

    Host.query.one()


def test_import_nmap_command(runner):
    """test nmap parser"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert host.os == 'Linux 3.8 - 4.6'
    assert sorted([x.port for x in host.services]) == [22, 25, 139, 445, 5432]
    tmpnote = Note.query.join(Service).filter(Note.host == host, Service.port == 25, Note.xtype == 'nmap.smtp-commands').one()
    assert 'PIPELINING' in json.loads(tmpnote.data)['output']


def test_import_nessus_command(runner):
    """test nessus parser"""

    result = runner.invoke(command, ['import', 'nessus', 'tests/server/data/parser-nessus-simple.xml'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert host.os == 'Microsoft Windows Vista'
    assert len(host.vulns) == 2
    assert sorted([x.port for x in host.services]) == [443]
    tmpvuln = Vuln.query.join(Service).filter(Vuln.host == host, Service.port == 443, Vuln.xtype == 'nessus.104631').one()
    assert 'CVE-1900-0000' in tmpvuln.refs
    note = Note.query.filter(Note.host == host, Note.xtype == 'hostnames').one()
    assert len(json.loads(note.data)) == 3


def test_import_manymap_command_zipfile(runner):
    """test manymap parser; zipfile import"""

    result = runner.invoke(command, ['import', 'manymap', 'tests/server/data/parser-manymap-job.zip'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert host.services[0].port == 18000
    assert host.services[0].info == 'product: Werkzeug httpd version: 0.15.5 extrainfo: Python 3.7.3'


def test_import_manymap_command_plaintext(runner):
    """test manymap parser; plaintext import"""

    result = runner.invoke(command, ['import', 'manymap', 'tests/server/data/parser-manymap-output-1.xml'])
    assert result.exit_code == 0

    Host.query.one()


def test_flush_command(runner, service, vuln, note):  # pylint: disable=unused-argument
    """flush storage database"""

    result = runner.invoke(command, ['flush'])
    assert result.exit_code == 0

    assert not Host.query.all()
    assert not Service.query.all()
    assert not Vuln.query.all()
    assert not Note.query.all()


def test_report_command(runner, host_factory, vuln_factory):
    """test vuln report command"""

    # additional test data required for 'misc' test (eg. multiple endpoints having same vuln)
    vuln = vuln_factory.create()
    vuln_name = vuln.name
    host1 = host_factory.create(address='127.3.3.1', hostname='testhost2.testdomain.tests')
    host2 = host_factory.create(address='127.3.3.2', hostname='testhost2.testdomain.tests')
    vuln_factory.create(host=host1, name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical)
    vuln_factory.create(host=host2, name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical)

    result = runner.invoke(command, ['report'])
    assert result.exit_code == 0
    assert f',"{vuln_name}",' in result.output
    assert ',"misc",' in result.output


def test_host_cleanup_command(runner, host_factory, service_factory):
    """test host_cleanup command"""

    host1 = host_factory.create(address='127.127.127.135', os='identified')
    host2 = host_factory.create(address='127.127.127.134')
    service_factory.create(host=host2, proto='tcp', port=1, state='anystate:reason')
    host3 = host_factory.create(address='127.127.127.133', hostname='xxx', os='', comment='')
    repr_host1, repr_host2, repr_host3 = repr(host1), repr(host2), repr(host3)
    host3_id = host3.id

    result = runner.invoke(command, ['host-cleanup', '--dry'])
    assert result.exit_code == 0

    assert repr_host1 not in result.output
    assert repr_host2 not in result.output
    assert repr_host3 in result.output
    assert Host.query.count() == 3

    result = runner.invoke(command, ['host-cleanup'])
    assert result.exit_code == 0

    hosts = Host.query.all()
    assert len(hosts) == 2
    assert host3_id not in [x.id for x in hosts]


def test_service_list_command(runner, service):
    """test services listing"""

    host = service.host

    result = runner.invoke(command, ['service-list', '--long', '--short'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['service-list'])
    assert result.exit_code == 0
    assert f'{service.proto}://{host.address}:{service.port}\n' == result.output

    result = runner.invoke(command, ['service-list', '--long'])
    assert result.exit_code == 0
    assert json.dumps(service.info) in result.output

    result = runner.invoke(command, ['service-list', '--short'])
    assert result.exit_code == 0
    assert result.output.strip() == host.address

    result = runner.invoke(command, ['service-list', '--short', '--hostnames'])
    assert result.exit_code == 0
    assert result.output.strip() == host.hostname

    result = runner.invoke(command, ['service-list', '--filter', f'Service.port=="{service.port}"'])
    assert result.exit_code == 0
    assert f'{service.proto}://{host.address}:{service.port}\n' == result.output


def test_service_cleanup_command(runner, host, service_factory, note_factory):
    """test service_cleanup command"""

    service1 = service_factory.create(host=host, proto='tcp', port=1, state='open:reason')
    service2 = service_factory.create(host=host, proto='tcp', port=1, state='filtered:reason')
    note_factory.create(host=host, service=service2, xtype='cleanuptest', data='atestdata')
    repr_service1, repr_service2 = repr(service1), repr(service2)
    service1_id = service1.id

    result = runner.invoke(command, ['service-cleanup', '--dry'])
    assert result.exit_code == 0

    assert repr_service1 not in result.output
    assert repr_service2 in result.output
    assert Service.query.count() == 2

    result = runner.invoke(command, ['service-cleanup'])
    assert result.exit_code == 0

    assert Note.query.count() == 0
    services = Service.query.all()
    assert len(services) == 1
    assert services[0].id == service1_id
