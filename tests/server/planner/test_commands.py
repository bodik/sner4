# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner command tests
"""

import pytest

from sner.server.planner.commands import command


@pytest.mark.filterwarnings('ignore:.*running the worker with superuser privileges.*')
def test_run_coverage(runner):
    """run planner in test mode to trigger coverage"""

    runner.app.config['SNER_PLANNER'] = {
        'import_jobs': [],
        'enqueue_servicelist': [],
        'rescan_services': {'interval': '1h', 'queue4': 'dummy', 'queue6': 'dummy'},
        'rescan_hosts': {'interval': '1h', 'queue4': 'dummy', 'queue6': 'dummy'},
        'discover_ipv4': {'interval': '1h', 'netranges': [], 'queue': 'dummy'},
        'discover_ipv6_dns': {'interval': '1h', 'netranges': [], 'queue': 'dummy'},
        'discover_ipv6_enum': {'interval': '1h', 'queue': 'dummy'},
        'enqueue_hostlist': [],
    }

    result = runner.invoke(command, ['run', '--test', '--debug'])
    assert result.exit_code == 0
