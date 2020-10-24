# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import csv
import json
from io import StringIO

from sner.server.storage.commands import command
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_import_command_invalidparser(runner):
    """test invalid parser"""

    result = runner.invoke(command, ['import', 'invalid', '/nonexistent'])
    assert result.exit_code == 1


def test_import_command_invalidpath(runner):
    """test invalid input path"""

    result = runner.invoke(command, ['import', 'nmap', '/nonexistent'])
    assert result.exit_code == 1


def test_import_command_nmap_job(runner):
    """test import nmap job"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-job.zip'])
    assert result.exit_code == 0

    assert Host.query.one()


def test_import_command_nmap_rawdata(runner):
    """test nmap parser"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert host.os == 'Linux 3.8 - 4.6'
    assert sorted([x.port for x in host.services]) == [22, 25, 139, 445, 5432]
    tmpnote = Note.query.join(Service).filter(Note.host == host, Service.port == 25, Note.xtype == 'nmap.smtp-commands').one()
    assert 'PIPELINING' in json.loads(tmpnote.data)['output']


def test_import_command_nessus(runner):
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


def test_import_command_manymap_job(runner):
    """test manymap parser; zipfile import"""

    result = runner.invoke(command, ['import', 'manymap', 'tests/server/data/parser-manymap-job.zip'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert host.services[0].port == 18000
    assert host.services[0].info == 'product: Werkzeug httpd version: 0.15.5 extrainfo: Python 3.7.3'


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
    vuln_factory.create(host=host2, name='trim test', xtype='x', severity=SeverityEnum.unknown, descr='A'*1001)

    result = runner.invoke(command, ['report'])
    assert result.exit_code == 0
    assert f',"{vuln_name}",' in result.output
    assert ',"misc",' in result.output
    assert ',"TRIMMED",' in result.output


def test_vuln_export_command(runner, host_factory, vuln_factory):
    """test vuln-export command"""

    host1 = host_factory.create(address='127.3.3.1', hostname='testhost2.testdomain.tests')
    host2 = host_factory.create(address='127.3.3.2', hostname='testhost2.testdomain.tests')
    vuln_factory.create(host=host1, name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical)
    vuln_factory.create(host=host2, name='vuln on many hosts', xtype='x', severity=SeverityEnum.critical)
    vuln_factory.create(host=host2, name='trim test', xtype='x', severity=SeverityEnum.unknown, descr='A'*1001)

    result = runner.invoke(command, ['vuln-export'])
    assert result.exit_code == 0
    assert ',"TRIMMED",' in result.output
    assert len(list(csv.reader(StringIO(result.stdout), delimiter=','))) == 6


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
