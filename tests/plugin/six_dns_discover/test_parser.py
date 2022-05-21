# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_dns_discover output parser tests
"""

from sner.plugin.six_dns_discover.parser import ParserModule


def test_host_list():
    """check host list extraction"""

    expected_hosts = ['::1']
    expected_notes = ['six_dns_discover.via']

    pidb = ParserModule.parse_path('tests/server/data/parser-six_dns_discover-job.zip')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.xtype for x in pidb.notes] == expected_notes
