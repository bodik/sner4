# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
jarm output parser tests
"""

from sner.plugin.jarm.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.0.0.1']
    # TODO: port cast int
    expected_services = ['443']
    expected_notes = ['jarm.fp']

    pidb = ParserModule.parse_path('tests/server/data/parser-jarm-job.zip')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.port for x in pidb.services] == expected_services
    assert [x.xtype for x in pidb.notes] == expected_notes
