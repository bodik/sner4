# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nuclei output parser tests
"""

from sner.plugin.nuclei.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.123.123.123']
    expected_vulns = ['nuclei.phpinfo-files', 'nuclei.dvwa-default-login', 'nuclei.git-config']
    expected_severities = ['low', 'critical', 'medium']

    pidb = ParserModule.parse_path('tests/server/data/parser-nuclei.json')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.vulns] == expected_vulns
    assert [x.severity for x in pidb.vulns] == expected_severities
    assert (
        'Git configuration was detected via the pattern /.git/config and log file on passed URLs.'
        in pidb.vulns.where(xtype='nuclei.git-config')[0].descr
    )
    assert 'CVE-2023-9999' in pidb.vulns.where(xtype='nuclei.dvwa-default-login')[0].refs


def test_parse_agent_output():
    """check agent output parsing"""

    pidb = ParserModule.parse_path('tests/server/data/parser-nuclei.zip')

    expected_hosts = ['127.0.0.1']
    expected_services = [18000, 22, 25]

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.port for x in pidb.services] == expected_services

    vuln = pidb.vulns.where(xtype='nuclei.openssh-detect')[0]
    assert 'SSH-2.0-OpenSSH_OpenSSH_8.4p1 Debian-5+deb11u1' in vuln.descr
    assert pidb.services[vuln.service_iid].port == 22


def test_parse_dns_template_output():
    """test import dns, does not have IP field"""

    ParserModule.parse_path('tests/server/data/parser-nuclei-dns.json')
