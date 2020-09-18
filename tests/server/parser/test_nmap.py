# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nmap output parser tests
"""

import pytest
from libnmap.parser import NmapParserException

from sner.server.parser.nmap import NmapParser


def test_xxe():
    """check if parser raises exception on xxe input"""

    # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    # etree exception is masked by library to it's own exception type
    with pytest.raises(NmapParserException):
        NmapParser.parse_path('tests/server/data/parser-nmap-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_host_handles = [{'host': '127.0.0.1'}]
    expected_service_handles = [
        {'host': '127.0.0.1', 'service': 'tcp/22'},
        {'host': '127.0.0.1', 'service': 'tcp/25'},
        {'host': '127.0.0.1', 'service': 'tcp/139'},
        {'host': '127.0.0.1', 'service': 'tcp/445'},
        {'host': '127.0.0.1', 'service': 'tcp/5432'}
    ]

    hosts, services, _, _ = NmapParser.parse_path('tests/server/data/parser-nmap-output.xml')

    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in services] == expected_service_handles
