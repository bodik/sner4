# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
inetverscan nmap-based output parser tests
"""

import pytest
from libnmap.parser import NmapParserException

from sner.server.parser.nmap import NmapParser


def test_xxe():
    """check if parser raises exception on xxe input"""

    # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
    # etree exception is masked by library to it's own exception type
    with pytest.raises(NmapParserException):
        NmapParser.import_file('tests/server/data/parser-nmap-xxe.xml')
