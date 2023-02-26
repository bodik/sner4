# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
testssl output parser tests
"""

import json

from sner.plugin.testssl.parser import ParserModule


def test_parse_path():
    """check basic parse_path impl"""

    expected_hosts = ['127.0.0.1']
    expected_services = [46865]
    expected_notes = ['testssl']

    pidb = ParserModule.parse_path('tests/server/data/parser-testssl-job.zip')

    assert [x.address for x in pidb.hosts] == expected_hosts
    assert [x.port for x in pidb.services] == expected_services
    assert [x.xtype for x in pidb.notes] == expected_notes
    assert 'DNS_CAArecord' in [x['id'] for x in json.loads(pidb.notes[0].data)['findings']['serverDefaults']]
