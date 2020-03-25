# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.command tests
"""

from sner.server.auth.commands import command
from sner.server.auth.models import User


def test_passwordreset_command(runner, test_user):
    """auth password reset command test"""

    result = runner.invoke(command, ['reset-password', 'notexists'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['reset-password', test_user.username])
    assert result.exit_code == 0

    user = User.query.filter(User.username == test_user.username).one()
    assert user.password != test_user.password
