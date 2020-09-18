# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
manymap nmap-based output parser tests
"""

import pytest
from libnmap.parser import NmapParserException

from sner.server.parser.manymap import ManymapParser


def test_xxe():
    """check if parser raises exception on xxe input"""

    # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    # etree exception is masked by library to it's own exception type
    with pytest.raises(NmapParserException):
        ManymapParser.parse_path('tests/server/data/parser-nmap-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_host_handles = ['host_id=127.0.0.1']
    expected_service_handles = ['host_id=127.0.0.1;service_id=tcp/18000']

    # test raw file parsing
    hosts, services, _, _ = ManymapParser.parse_path('tests/server/data/parser-manymap-output-1.xml')
    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in services] == expected_service_handles

    # test job archive parsing
    hosts, services, _, _ = ManymapParser.parse_path('tests/server/data/parser-manymap-job.zip')
    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in services] == expected_service_handles
