# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shodan output parser tests
"""

from sner.plugin.shodan.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.6.1.1']
    expected_vuln = 'shodan.CVE-2019-20372'

    pidb = ParserModule.parse_path('tests/server/data/parser-shodan.jsonlines')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert expected_vuln in [x.xtype for x in pidb.vulns]
