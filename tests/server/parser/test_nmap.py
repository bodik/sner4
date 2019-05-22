"""nmap output parser tests"""

import pytest
from libnmap.parser import NmapParserException

from sner.server.parser.nmap import NmapParser


def test_xxe(app):
    """check if parser raises exception on xxe input"""

    with open('tests/server/data/parser-nmap-xxe.xml') as ftmp:
        # https://docs.python.org/3/library/xml.html#xml-vulnerabilities
        # etree exception is masked by library to it's own exception type
        with pytest.raises(NmapParserException):
            NmapParser.data_to_storage(ftmp.read())
