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
        ManymapParser.import_file('tests/server/data/parser-nmap-xxe.xml')
