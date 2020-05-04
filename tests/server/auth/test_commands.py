# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.command tests
"""

from sner.server.auth.commands import command
from sner.server.auth.models import User


def test_passwordreset_command(runner, user):
    """auth password reset command test"""

    old_password = user.password

    result = runner.invoke(command, ['reset-password', 'notexists'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['reset-password', user.username])
    assert result.exit_code == 0

    tuser = User.query.get(user.id)
    assert tuser.password != old_password
