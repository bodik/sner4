# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nessus output parser tests
"""

import pytest
from defusedxml.common import EntitiesForbidden

from sner.plugin.nessus.parser import ParserModule
from sner.server.parser import HostHandle, ServiceHandle


def test_xxe(app):  # pylint: disable=unused-argument
    """check if parser resolves external entities"""

    with pytest.raises(EntitiesForbidden):
        ParserModule.parse_path('tests/server/data/parser-nessus-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = [HostHandle('127.128.129.130')]
    expected_vulns = [
        (expected_hosts[0], ServiceHandle(expected_hosts[0], 'tcp', 443), 'nessus.104631'),
        (expected_hosts[0], None, 'nessus.19506')
    ]

    pidb = ParserModule.parse_path('tests/server/data/parser-nessus-simple.xml')

    assert [x.handle for x in pidb.hosts.values()] == expected_hosts
    assert [x.handle for x in pidb.vulns.values()] == expected_vulns
