"""storage commands tests"""

import json
import re

import pytest

from sner.server.command.storage import storage_command
from sner.server.model.storage import Host, Note, Service, Vuln


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


@pytest.mark.skip(reason='would note test flushing database')
def test_flush_command():
    """flush storage database; no separate test db, test not implemented"""
    pass


def test_report_command(runner, test_vuln):
    """test vuln report command"""

    result = runner.invoke(storage_command, ['report'])
    assert result.exit_code == 0
    assert ',"%s",' % test_vuln.name in result.output
