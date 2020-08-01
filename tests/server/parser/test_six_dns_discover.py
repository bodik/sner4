# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_dns_discover output parser tests
"""

from sner.server.parser.six_dns_discover import SixDnsDiscoverParser


def test_host_list():
    """check host list extraction"""

    expected = ['::1']
    assert SixDnsDiscoverParser.host_list('tests/server/data/parser-six_dns_discover-job.zip') == expected
