# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
icmp_up output parser tests
"""

from sner.plugin.icmp_up.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['192.168.0.1', '::1', '127.1.2.3', '8.8.8.8']
    expected_notes = ['icmp_up'] * 4

    pidb = ParserModule.parse_path('tests/server/data/parser-icmp_up.txt')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.notes] == expected_notes


def test_parse_agent_output():
    """check agent output parsing"""
    expected_hosts = ['127.1.1.1', "::1"]
    expected_notes = ['icmp_up'] * 2

    pidb = ParserModule.parse_path('tests/server/data/parser-icmp_up.zip')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.notes] == expected_notes
