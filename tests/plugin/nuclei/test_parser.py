# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nuclei output parser tests
"""

from sner.plugin.nuclei.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.123.123.123']
    expected_vulns = ['phpinfo-files', 'dvwa-default-login', 'git-config']
    expected_severities = ['low', 'critical', 'medium']

    pidb = ParserModule.parse_path('tests/server/data/parser-nuclei.json')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.vulns] == expected_vulns
    assert [x.severity for x in pidb.vulns] == expected_severities
    assert 'Git configuration was detected via the pattern /.git/config and log file on passed URLs.' in pidb.vulns.where(xtype='git-config')[0].descr
    assert 'CVE-2023-9999' in pidb.vulns.where(xtype='dvwa-default-login')[0].refs

    pidb = ParserModule.parse_path('tests/server/data/parser-nuclei.zip')

    assert [x.address for x in pidb.hosts] == ['127.111.111.111']
