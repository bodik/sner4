# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
jarm output parser tests
"""

from sner.plugin.jarm.parser import JarmParser


def test_parse_path():
    """check basic parse_path impl"""

    expected_host_handles = [{'host': '127.0.0.1'}]
    expected_service_handles = [{'host': '127.0.0.1', 'service': 'tcp/443'}]
    expected_note_handles = [{'host': '127.0.0.1', 'service': 'tcp/443', 'note': 'jarm.fp'}]

    hosts, services, _, notes = JarmParser.parse_path('tests/server/data/parser-jarm-job.zip')

    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in services] == expected_service_handles
    assert [x.handle for x in notes] == expected_note_handles
