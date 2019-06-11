"""auth commands testcases"""

from sner.server.command.auth import auth_command
from sner.server.model.auth import User


def test_auth_passwordreset_command(runner, test_user):
    """auth password reset command test"""

    result = runner.invoke(auth_command, ['passwordreset', 'notexists'])
    assert result.exit_code == 1

    result = runner.invoke(auth_command, ['passwordreset', test_user.username])
    assert result.exit_code == 0

    user = User.query.filter(User.username == test_user.username).one_or_none()
    assert user.password != test_user.password
