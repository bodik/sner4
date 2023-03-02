# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import csv
import functools
import json
from io import StringIO
from unittest.mock import patch

from flask import current_app

import sner.server.storage.vulnsearch
from sner.server.storage.commands import command
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_import_command_errorhandling(runner):
    """test invalid parser"""

    # invalid parser
    result = runner.invoke(command, ['import', 'invalid', 'dummy'])
    assert result.exit_code == 1

    # parse exception handling
    result = runner.invoke(command, ['import', 'nmap', 'sner.yaml.example', 'notexist'])
    assert result.exit_code == 0


def test_import_command_dryrun(runner):
    """test import dry run"""

    result = runner.invoke(command, ['import', '--dry', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0
    assert 'new host:' in result.output
    assert 'new service:' in result.output
    assert 'new note:' in result.output

    result = runner.invoke(command, ['import', '--dry', 'nessus', 'tests/server/data/parser-nessus-simple.xml'])
    assert result.exit_code == 0
    assert 'new host:' in result.output
    assert 'new service:' in result.output
    assert 'new vuln:' in result.output


def test_flush_command(runner, service, vuln, note):  # pylint: disable=unused-argument
    """flush storage database"""

    result = runner.invoke(command, ['flush'])
    assert result.exit_code == 0

    assert not Host.query.all()
    assert not Service.query.all()
    assert not Vuln.query.all()
    assert not Note.query.all()


def test_vuln_report_command(runner, host_factory, vuln_factory):
    """test vuln-report command"""

    # additional test data required for 'misc' test (eg. multiple endpoints having same vuln)
    vuln = vuln_factory.create()
    vuln_name = vuln.name
    host1 = host_factory.create(address='127.3.3.1', hostname='testhost2.testdomain.tests')
    host2 = host_factory.create(address='::127:3:3:2', hostname='testhost2.testdomain.tests')
    vuln_factory.create(host=host1, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='trim test', xtype='x', severity=SeverityEnum.UNKNOWN, descr='A'*1001)

    result = runner.invoke(command, ['vuln-report'])
    assert result.exit_code == 0
    assert f',"{vuln_name}",' in result.output
    assert ',"misc",' in result.output
    assert ',"TRIMMED",' in result.output
    assert '[::127:3:3:2]' in result.output

    result = runner.invoke(command, ['vuln-report', '--group_by_host', '--filter', 'Host.address == "127.3.3.1"'])
    assert result.exit_code == 0

    result = runner.invoke(command, ['vuln-report', '--filter', 'invalid'])
    assert result.exit_code == 1


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


def test_syncvulnsearch_command(runner, note_factory):
    """test sync-vulnsearch command"""

    @functools.lru_cache(maxsize=256)
    def cvefor_mock(_1, _2):
        """
        mock external cvesearch service.
        note: function prototype should match original so the cache stats debug code does not break.
        """

        return [{
            'id': 'CVE-0000-0000',
            'summary': 'mock summary',
            'cvss': 0.0,
        }]

    def es_bulk_mock(_1, _2):
        """es bulk mock"""

    def update_managed_indices_mock(_1, _2):
        """update_managed_indices_mock mock"""

    note_factory.create(xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor2:product2"]')
    note_factory.create_batch(1000, xtype='cpe', data='["cpe:/a:vendor3:product3:0.0"]')
    note_factory.create(xtype='cpe', data='["invalid"]')

    patch_cvefor = patch.object(sner.server.storage.vulnsearch, 'cvefor', cvefor_mock)
    patch_esbulk = patch.object(sner.server.storage.vulnsearch, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.vulnsearch, 'update_managed_indices', update_managed_indices_mock)

    current_app.config['SNER_VULNSEARCH'] = {
        'cvesearch': 'http://dummy:80',
        'esd': 'http://dummy:80'
    }

    with patch_cvefor, patch_esbulk, patch_update:
        result = runner.invoke(command, ['sync-vulnsearch'])

    assert result.exit_code == 0


def test_syncvulnsearch_command_params(runner):
    """tests param/config handling"""

    def update_managed_indices_mock(_1, _2):
        """update_managed_indices_mock mock"""

    result = runner.invoke(command, ['sync-vulnsearch', '--esd', 'dummy'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['sync-vulnsearch', '--cvesearch', 'dummy'])
    assert result.exit_code == 1

    patch_update = patch.object(sner.server.storage.vulnsearch, 'update_managed_indices', update_managed_indices_mock)
    with patch_update:
        result = runner.invoke(command, ['sync-vulnsearch', '--cvesearch', 'http://dummy:80', '--esd', 'http://dummy:80'])
    assert result.exit_code == 0
