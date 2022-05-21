# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nessus output parser tests
"""

import pytest
from defusedxml.common import EntitiesForbidden

from sner.plugin.nessus.parser import ParserModule


def test_xxe(app):  # pylint: disable=unused-argument
    """check if parser resolves external entities"""

    with pytest.raises(EntitiesForbidden):
        ParserModule.parse_path('tests/server/data/parser-nessus-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.128.129.130']
    expected_vulns = ['nessus.104631', 'nessus.19506']

    pidb = ParserModule.parse_path('tests/server/data/parser-nessus-simple.xml')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.vulns] == expected_vulns
