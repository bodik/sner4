"""pytest config and fixtures"""

from uuid import uuid4

import pytest
from flask import url_for
from webtest import TestApp

from sner.server import db
from sner.server.model.auth import User
# import all fixtures here; they will be available in all tests, import on module specific level would trigger redefined-outer-name
from tests.server.model.auth import test_user  # noqa: F401  pylint: disable=unused-import
from tests.server.model.scheduler import test_excl_network, test_excl_regex, test_job, test_job_completed, test_queue, test_target, test_task  # noqa: F401,E501  pylint: disable=unused-import
from tests.server.model.storage import test_host, test_note, test_service, test_vuln  # noqa: F401  pylint: disable=unused-import


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

    tmp_password = str(uuid4())
    tmp_user = User(username='pytest_user', password=tmp_password, active=True, roles=roles)
    db.session.add(tmp_user)
    db.session.commit()

    form = clnt.get(url_for('auth.login_route')).form
    form['username'] = tmp_user.username
    form['password'] = tmp_password
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
