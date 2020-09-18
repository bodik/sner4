# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_dns_discover output parser tests
"""

from sner.server.parser.six_dns_discover import SixDnsDiscoverParser


def test_host_list():
    """check host list extraction"""

    expected_host_handles = ['host_id=::1']
    expected_note_handles = ['host_id=::1']

    hosts, _, _, notes = SixDnsDiscoverParser.parse_path('tests/server/data/parser-six_dns_discover-job.zip')

    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in notes] == expected_note_handles
