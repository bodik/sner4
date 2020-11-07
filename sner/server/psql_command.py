# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server psql command module
"""

from os import execv
from shutil import which

import click
from flask import current_app
from flask.cli import with_appcontext

from sner.server.extensions import db


@click.command(name='psql', help='run psql connected to configured database', context_settings={'ignore_unknown_options': True})
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@with_appcontext
def command(args):
    """run psql connected to configured database"""

    db.session.close()
    cmd = [which('psql'), current_app.config['SQLALCHEMY_DATABASE_URI']] + list(args)
    execv(cmd[0], cmd)
