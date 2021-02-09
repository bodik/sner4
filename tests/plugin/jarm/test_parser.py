# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
jarm output parser tests
"""

from sner.plugin.jarm.parser import ParserModule
from sner.server.parser import DataHandle, HostHandle, ServiceHandle


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = [HostHandle('127.0.0.1')]
    # TODO: port cast int
    expected_services = [ServiceHandle(expected_hosts[0], 'tcp', '443')]
    expected_notes = [DataHandle(expected_hosts[0], expected_services[0], 'jarm.fp')]

    pidb = ParserModule.parse_path('tests/server/data/parser-jarm-job.zip')

    assert [x.handle for x in pidb.hosts.values()] == expected_hosts
    assert [x.handle for x in pidb.services.values()] == expected_services
    assert [x.handle for x in pidb.notes.values()] == expected_notes
