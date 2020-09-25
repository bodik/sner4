# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
test planner steps unittests
"""

from sner.server.parser.core import ParsedService
from sner.server.planner.core import Context
from sner.server.planner.steps import project_servicelist


def test_project_servicelist():
    """test project servicelist"""

    ctx = Context()
    ctx['data'] = {'services': [
        ParsedService(handle={'host': '127.0.2.1', 'service': 'tcp/1'}, proto='tcp', port='1'),
        ParsedService(handle={'host': '::1', 'service': 'tcp/1'}, proto='tcp', port='1')
    ]}
    project_servicelist(ctx)

    expected = ['tcp://127.0.2.1:1', 'tcp://[::1]:1']
    assert ctx['data'] == expected
