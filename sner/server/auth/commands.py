# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth commands
"""

import sys

import click
from flask import current_app
from flask.cli import with_appcontext

from sner.server.auth.models import User
from sner.server.extensions import db
from sner.server.password_supervisor import PasswordSupervisor as PWS


@click.group(name='auth', help='sner.server auth management')
def command():
    """auth commands container"""


@command.command(name='reset-password', help='reset password')
@click.argument('username')
@with_appcontext
def passwordreset(username):
    """reset password for username"""

    user = User.query.filter(User.username == username).one_or_none()
    if not user:
        current_app.logger.error('no such user')
        sys.exit(1)

    tmp_password = PWS().generate()
    user.password = tmp_password
    db.session.commit()
    current_app.logger.info('new password "%s:%s"' % (user.username, tmp_password))
