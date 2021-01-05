# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
test planner steps unittests
"""

from sner.server.parser.core import ParsedService
from sner.server.planner.core import Context
from sner.server.planner.steps import filter_tarpits, project_servicelist
from sner.server.scheduler.models import Job


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


def test_filter_tarpits(app):  # pylint: disable=unused-argument
    """test filter tarpits"""

    ctx = Context()
    ctx['job'] = Job(id='atestjobid')
    ctx['data'] = {'services': [
        ParsedService(handle={'host': '127.0.3.1', 'service': 'tcp/1'}, proto='tcp', port='1')
    ]}
    for port in range(1, 500):
        ctx['data']['services'].append(ParsedService(handle={'host': '127.0.4.1', 'service': f'tcp/{port}'}, proto='tcp', port=f'{port}'))
    filter_tarpits(ctx)

    assert len(ctx['data']['services']) == 1
