# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
db commands tests
"""

from pathlib import Path

from flask import current_app
from sqlalchemy import inspect

from sner.server.dbx_command import command
from sner.server.extensions import db
from sner.server.scheduler.models import Target
from sner.server.storage.models import Vuln


def test_init_command(runner):
    """dbx init test"""

    result = runner.invoke(command, ['init'])
    assert result.exit_code == 0


def test_initdata_command(runner):
    """dbx initdata test"""

    result = runner.invoke(command, ['init-data'])
    assert result.exit_code == 0

    assert Target.query.all()
    assert Vuln.query.all()


def test_remove_command(runner):
    """dbx remove test"""

    test_dir = Path(f'{current_app.config["SNER_VAR"]}/dbremovetest')
    test_path = Path(f'{current_app.config["SNER_VAR"]}/dbremovetest.txt')
    test_path.write_text('db remove test', 'utf-8')
    test_dir.mkdir()

    result = runner.invoke(command, ['remove'])
    assert result.exit_code == 0

    assert not inspect(db.engine).get_table_names()
    assert not test_dir.exists()
    assert not test_path.exists()
