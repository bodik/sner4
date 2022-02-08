# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner command tests
"""


from sner.server.planner.commands import command


def test_command_run(runner):
    """run planner in test mode to trigger coverage"""

    result = runner.invoke(command, ['run', '--oneshot'])
    assert result.exit_code == 0
