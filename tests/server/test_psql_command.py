# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
psql commands tests
"""

from unittest.mock import patch

from flask import current_app

import sner.server.psql_command
from sner.server.psql_command import command


def test_psql_command(runner):
    """test psql command"""

    patch_execv = patch.object(sner.server.psql_command, 'execv', print)

    with patch_execv:
        result = runner.invoke(command)
    assert result.exit_code == 0

    assert 'psql' in result.stdout
    assert current_app.config['SQLALCHEMY_DATABASE_URI'] in result.stdout
