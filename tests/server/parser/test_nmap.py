# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nmap output parser tests
"""

import pytest
from libnmap.parser import NmapParserException

from sner.server.parser import ServiceListItem
from sner.server.parser.nmap import NmapParser


def test_xxe():
    """check if parser raises exception on xxe input"""

    # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    # etree exception is masked by library to it's own exception type
    with pytest.raises(NmapParserException):
        NmapParser.import_file('tests/server/data/parser-nmap-xxe.xml')


def test_service_list():
    """check service list extraction"""

    expected = [
        ServiceListItem(service='tcp://127.0.0.1:22', state='open:syn-ack'),
        ServiceListItem(service='tcp://127.0.0.1:25', state='open:syn-ack'),
        ServiceListItem(service='tcp://127.0.0.1:139', state='open:syn-ack'),
        ServiceListItem(service='tcp://127.0.0.1:445', state='open:syn-ack'),
        ServiceListItem(service='tcp://127.0.0.1:5432', state='open:syn-ack')
    ]
    assert NmapParser.service_list('tests/server/data/parser-nmap-output.xml') == expected
