# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
db commands tests
"""

import os

from flask import current_app

from sner.server import db
from sner.server.command.db import db_command
from sner.server.model.scheduler import Target
from sner.server.model.storage import Vuln


def test_dbinit_command(runner):
    """db init test"""

    result = runner.invoke(db_command, ['init'])
    assert result.exit_code == 0


def test_dbinitdata_command(runner):
    """db initdata test"""

    result = runner.invoke(db_command, ['initdata'])
    assert result.exit_code == 0

    assert Target.query.all()
    assert Vuln.query.all()


def test_dbremove_command(runner):
    """db remove test"""

    test_dir = '%s/dbremovetest' % current_app.config['SNER_VAR']
    test_path = '%s/dbremovetest.txt' % current_app.config['SNER_VAR']
    with open(test_path, 'w') as ftmp:
        ftmp.write('db remove test')
    os.mkdir(test_dir)

    result = runner.invoke(db_command, ['remove'])
    assert result.exit_code == 0

    assert not db.engine.table_names()
    assert not os.path.exists(test_dir)
    assert not os.path.exists(test_path)
