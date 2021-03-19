# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_dns_discover output parser tests
"""

from sner.plugin.six_dns_discover.parser import ParserModule
from sner.server.parser import DataHandle, HostHandle


def test_host_list():
    """check host list extraction"""

    expected_hosts = [HostHandle('::1')]
    expected_notes = [DataHandle(expected_hosts[0], None, None, 'six_dns_discover.via')]

    pidb = ParserModule.parse_path('tests/server/data/parser-six_dns_discover-job.zip')

    assert [x.handle for x in pidb.hosts.values()] == expected_hosts
    assert [x.handle for x in pidb.notes.values()] == expected_notes
