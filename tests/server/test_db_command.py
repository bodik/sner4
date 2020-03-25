# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
db commands tests
"""

import os

from flask import current_app

from sner.server.db_command import command
from sner.server.extensions import db
from sner.server.scheduler.models import Target
from sner.server.storage.models import Vuln


def test_init_command(runner):
    """db init test"""

    result = runner.invoke(command, ['init'])
    assert result.exit_code == 0


def test_initdata_command(runner):
    """db initdata test"""

    result = runner.invoke(command, ['init-data'])
    assert result.exit_code == 0

    assert Target.query.all()
    assert Vuln.query.all()


def test_remove_command(runner):
    """db remove test"""

    test_dir = '%s/dbremovetest' % current_app.config['SNER_VAR']
    test_path = '%s/dbremovetest.txt' % current_app.config['SNER_VAR']
    with open(test_path, 'w') as ftmp:
        ftmp.write('db remove test')
    os.mkdir(test_dir)

    result = runner.invoke(command, ['remove'])
    assert result.exit_code == 0

    assert not db.engine.table_names()
    assert not os.path.exists(test_dir)
    assert not os.path.exists(test_path)
