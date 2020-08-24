# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_enum_discover output parser tests
"""

from sner.server.parser.six_enum_discover import SixEnumDiscoverParser


def test_host_list():
    """check host list extraction"""

    expected = ['::1']
    assert SixEnumDiscoverParser.host_list('tests/server/data/parser-six_enum_discover-job.zip') == expected
