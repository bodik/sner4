# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nessus output parser tests
"""

import pytest
from defusedxml.common import EntitiesForbidden

from sner.server.parser.nessus import NessusParser


def test_xxe(app):  # pylint: disable=unused-argument
    """check if parser resolves external entities"""

    with pytest.raises(EntitiesForbidden):
        NessusParser.parse_path('tests/server/data/parser-nessus-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_host_handles = ['host_id=127.128.129.130']
    expected_vuln_handles = ['host_id=127.128.129.130;vuln_id=104631;service_id=tcp/443', 'host_id=127.128.129.130;vuln_id=19506']

    hosts, _, vulns, _ = NessusParser.parse_path('tests/server/data/parser-nessus-simple.xml')

    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in vulns] == expected_vuln_handles
