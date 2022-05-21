# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
manymap nmap-based output parser tests
"""

from sner.plugin.manymap.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.0.0.1']
    expected_services = [18000]

    pidb = ParserModule.parse_path('tests/server/data/parser-manymap-job.zip')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.port for x in pidb.services] == expected_services
