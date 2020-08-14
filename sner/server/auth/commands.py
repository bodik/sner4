# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth commands
"""

import sys
from uuid import uuid4

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
def reset_password(username):
    """reset password for username"""

    user = User.query.filter(User.username == username).one_or_none()
    if not user:
        current_app.logger.error('no such user')
        sys.exit(1)

    tmp_password = PWS.generate()
    user.password = tmp_password
    db.session.commit()
    current_app.logger.info('new password "%s:%s"' % (user.username, tmp_password))


@command.command(name='add-agent', help='add agent')
@with_appcontext
def add_agent():
    """add new agent"""

    apikey = PWS.generate_apikey()
    agent = User(
        username=f'agent_{uuid4()}',
        apikey=apikey,
        active=True,
        roles=['agent']
    )
    db.session.add(agent)
    db.session.commit()
    current_app.logger.info(f'new agent {agent.username} apikey {apikey}')
