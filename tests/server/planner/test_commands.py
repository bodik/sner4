# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner command tests
"""


from sner.server.planner.commands import command


def test_command_run(runner):
    """run planner in test mode to trigger coverage"""

    runner.app.config['SNER_PLANNER']['pipelines'] = [
        {'type': 'queue', 'steps': [{'step': 'stop_pipeline'}]},
        {'type': 'interval', 'name': 'intervaltest', 'interval': '1h', 'steps': []},
        {'type': 'generic', 'steps': []},
        {'invalid': 0},
    ]

    result = runner.invoke(command, ['run', '--oneshot'])
    assert result.exit_code == 0
