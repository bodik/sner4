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
        NessusParser.import_file('tests/server/data/parser-nessus-xxe.xml')
