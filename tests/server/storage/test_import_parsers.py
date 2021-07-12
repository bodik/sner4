# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
individual parser plugin tests
"""

import json

from sner.server.storage.commands import command
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_import_command_nmap_job(runner):
    """test import nmap job"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-job.zip'])
    assert result.exit_code == 0

    assert Host.query.one()


def test_import_command_nmap_rawdata(runner):
    """test nmap parser"""

    result = runner.invoke(command, ['import', 'nmap', 'tests/server/data/parser-nmap-output.xml'])
    assert result.exit_code == 0

    # run twice to check update scheme of the import algorithms
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


def test_import_command_nc(runner):
    """test nc parser"""

    result = runner.invoke(command, ['import', 'nc', 'tests/server/data/parser-nc.txt'])
    assert result.exit_code == 0

    host = Host.query.one()
    assert len(host.services) == 2
    assert sorted([x.port for x in host.services]) == [21, 22]

