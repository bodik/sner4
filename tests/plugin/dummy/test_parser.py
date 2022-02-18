# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
dummy output parser tests
"""

from sner.plugin.dummy.parser import ParserModule
from sner.server.parser import HostHandle


def test_host_list():
    """check host list extraction"""

    expected_hosts = [HostHandle('1'), HostHandle('2')]

    pidb = ParserModule.parse_path('tests/server/data/parser-dummy-job.zip')

    assert [x.handle for x in pidb.hosts.values()] == expected_hosts
