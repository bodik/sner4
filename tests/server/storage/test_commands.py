# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import csv
import json
from io import StringIO
from unittest.mock import Mock, patch

import sner.server.storage.elastic
from sner.server.storage.commands import command
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_import_command_errorhandling(runner):
    """test invalid parser"""

    # invalid parser
    result = runner.invoke(command, ['import', '--parser', 'invalid', 'dummy'])
    assert result.exit_code == 1

    # parse exception handling
    result = runner.invoke(command, ['import', '--parser', 'nmap', 'sner.yaml.example', 'notexist'])
    assert result.exit_code == 0


def test_import_command_dryrun(runner):
    """test import dry run"""

    result = runner.invoke(command, ['import', '--dry', '--parser', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0
    assert 'new host:' in result.output
    assert 'new service:' in result.output
    assert 'new note:' in result.output

    result = runner.invoke(command, ['import', '--dry', '--parser', 'nessus', 'tests/server/data/parser-nessus-simple.xml'])
    assert result.exit_code == 0
    assert 'new host:' in result.output
    assert 'new service:' in result.output
    assert 'new vuln:' in result.output

    result = runner.invoke(command, ['import', '--dry', 'tests/server/data/parser-jarm-job.zip'])
    assert result.exit_code == 0
    assert 'new host:' in result.output
    assert 'new service:' in result.output
    assert 'new note:' in result.output

    result = runner.invoke(command, ['import', '--dry', 'tests/server/data/parser-dummy-job.zip'])
    assert result.exit_code == 0


def test_flush_command(runner, service, vuln, note):  # pylint: disable=unused-argument
    """flush storage database"""

    result = runner.invoke(command, ['flush'])
    assert result.exit_code == 0

    assert not Host.query.all()
    assert not Service.query.all()
    assert not Vuln.query.all()
    assert not Note.query.all()


def test_vuln_report_command(runner, vuln):  # pylint: disable=unused-argument
    """test vuln-report command"""

    result = runner.invoke(command, ['vuln-report'])
    assert result.exit_code == 0
    assert len(result.output.splitlines()) > 1


def test_vuln_export_command(runner, host_factory, vuln_factory):
    """test vuln-export command"""

    host1 = host_factory.create(address='127.3.3.1', hostname='testhost2.testdomain.tests')
    host2 = host_factory.create(address='::127:3:3:2', hostname='testhost2.testdomain.tests')
    vuln_factory.create(host=host1, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='trim test', xtype='x', severity=SeverityEnum.UNKNOWN, descr='A'*1001)

    result = runner.invoke(command, ['vuln-export'])
    assert result.exit_code == 0
    assert ',"TRIMMED",' in result.output
    assert '[::127:3:3:2]' in result.output
    assert len(list(csv.reader(StringIO(result.stdout), delimiter=','))) == 6

    result = runner.invoke(command, ['vuln-export', '--filter', 'Host.address == "127.3.3.1"'])
    assert result.exit_code == 0

    result = runner.invoke(command, ['vuln-export', '--filter', 'invalid'])
    assert result.exit_code == 1


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

    result = runner.invoke(command, ['service-list', '--simple'])
    assert result.exit_code == 0
    assert result.output.strip() == f'{host.address} {service.port}'

    result = runner.invoke(command, ['service-list', '--filter', f'Service.port=="{service.port}"'])
    assert result.exit_code == 0
    assert result.output.strip() == f'{service.proto}://{host.address}:{service.port}'

    result = runner.invoke(command, ['service-list', '--filter', 'invalid'])
    assert result.exit_code == 1


def test_rebuild_vulnsearch_elastic_command(runner):
    """tests param/config handling"""

    result = runner.invoke(command, ['rebuild-vulnsearch-elastic'])
    assert result.exit_code == 1

    update_alias_mock = Mock()
    with (
        patch.object(sner.server.storage.elastic.BulkIndexer, 'initialize', Mock()),
        patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    ):
        result = runner.invoke(command, ['rebuild-vulnsearch-elastic', '--cvesearch', 'http://dummy:80', '--esd', 'http://dummy:80'])

    assert result.exit_code == 0
    update_alias_mock.assert_called_once()


def test_rebuild_vulnsearch_localdb_command(runner):
    """tests rebuild vulnsearch localdb command"""

    result = runner.invoke(command, ['rebuild-vulnsearch-localdb'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['rebuild-vulnsearch-localdb', '--cvesearch', 'http://dummy:80'])
    assert result.exit_code == 0


def test_rebuild_elasticstorage_command(runner):
    """tests param/config handling"""

    result = runner.invoke(command, ['rebuild-elasticstorage'])
    assert result.exit_code == 1

    update_alias_mock = Mock()
    with (
        patch.object(sner.server.storage.elastic.BulkIndexer, 'initialize', Mock()),
        patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    ):
        result = runner.invoke(command, ['rebuild-elasticstorage', '--esd', 'http://dummy:80'])

    assert result.exit_code == 0
    update_alias_mock.assert_called()


def test_rebuild_versioninfo_command(runner):
    """tests rebuild versioninfo command"""

    result = runner.invoke(command, ['rebuild-versioninfo'])
    assert result.exit_code == 0
