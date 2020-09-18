# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_enum_discover output parser tests
"""

from sner.server.parser.six_enum_discover import SixEnumDiscoverParser


def test_host_list():
    """check host list extraction"""

    expected_host_handles = [{'host': '::1'}]

    hosts, _, _, _ = SixEnumDiscoverParser.parse_path('tests/server/data/parser-six_enum_discover-job.zip')

    assert [x.handle for x in hosts] == expected_host_handles
