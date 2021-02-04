# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
manymap nmap-based output parser tests
"""

from sner.plugin.manymap.parser import ManymapParser


def test_parse_path():
    """check basic parse_path impl"""

    expected_host_handles = [{'host': '127.0.0.1'}]
    expected_service_handles = [{'host': '127.0.0.1', 'service': 'tcp/18000'}]

    hosts, services, _, _ = ManymapParser.parse_path('tests/server/data/parser-manymap-job.zip')
    assert [x.handle for x in hosts] == expected_host_handles
    assert [x.handle for x in services] == expected_service_handles
