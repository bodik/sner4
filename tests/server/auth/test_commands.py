# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.command tests
"""

from sner.server.auth.commands import command
from sner.server.auth.models import User
from sner.server.password_supervisor import PasswordSupervisor as PWS


def test_resetpassword_command(runner, user):
    """auth password reset command test"""

    old_password = user.password

    result = runner.invoke(command, ['reset-password', 'notexists'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['reset-password', user.username])
    assert result.exit_code == 0

    tuser = User.query.get(user.id)
    assert tuser.password != old_password


def test_addagent_command(runner):
    """add agent command test"""

    result = runner.invoke(command, ['add-agent'])
    assert result.exit_code == 0
    new_apikey = result.output.strip().split(' ')[-1]
    assert User.query.first().apikey == PWS.hash_simple(new_apikey)
