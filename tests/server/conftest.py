# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
pytest config and fixtures
"""

import pytest
from flask import url_for
from webtest import TestApp

from sner.server.auth.models import User
from sner.server.extensions import db
from sner.server.password_supervisor import PasswordSupervisor as PWS


@pytest.fixture
def client(app):  # pylint: disable=redefined-outer-name
    """create webtest testapp client"""
    return TestApp(app)


@pytest.fixture
def runner(app):  # pylint: disable=redefined-outer-name
    """create cli test runner"""
    return app.test_cli_runner()


def client_in_roles(clnt, roles):
    """create user role and login client to role(s)"""

    password = PWS.generate()
    user = User(username='pytest_user', password=password, active=True, roles=roles)
    db.session.add(user)
    db.session.commit()

    form = clnt.get(url_for('auth.login_route')).form
    form['username'] = user.username
    form['password'] = password
    form.submit()
    return clnt


@pytest.fixture
def cl_user(client):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role user"""

    yield client_in_roles(client, ['user'])


@pytest.fixture
def cl_operator(client):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role operator"""

    yield client_in_roles(client, ['user', 'operator'])


@pytest.fixture
def cl_admin(client):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role admin"""

    yield client_in_roles(client, ['user', 'operator', 'admin'])
