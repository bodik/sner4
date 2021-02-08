# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nmap output parser tests
"""

import pytest
from libnmap.parser import NmapParserException

from sner.plugin.nmap.parser import ParserModule


def test_xxe():
    """check if parser raises exception on xxe input"""

    # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    # etree exception is masked by library to it's own exception type
    with pytest.raises(NmapParserException):
        ParserModule.parse_path('tests/server/data/parser-nmap-xxe.xml')


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.0.0.1']
    expected_services = [
        ('127.0.0.1', 'tcp', 22),
        ('127.0.0.1', 'tcp', 25),
        ('127.0.0.1', 'tcp', 139),
        ('127.0.0.1', 'tcp', 445),
        ('127.0.0.1', 'tcp', 5432)
    ]

    pidb = ParserModule.parse_path('tests/server/data/parser-nmap-output.xml')

    assert [x.handle for x in pidb.hosts.values()] == expected_hosts
    assert [x.handle for x in pidb.services.values()] == expected_services