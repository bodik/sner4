# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner pytest config and fixtures
"""

import os
import shutil
from tempfile import mkdtemp

import pytest
from pytest_factoryboy import register as factoryboy_register

from sner.server.app import create_app
from sner.server.auth.models import User
from sner.server.extensions import db
from sner.server.dbx_command import db_remove
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server.auth.models import UserFactory, WebauthnCredentialFactory
from tests.server.scheduler.models import (
    ExclNetworkFactory,
    ExclRegexFactory,
    JobFactory,
    JobCompletedFactory,
    QueueFactory,
    TargetFactory
)
from tests.server.storage.models import HostFactory, NoteFactory, ServiceFactory, VulnFactory


@pytest.fixture
def app():
    """yield application as pytest fixture"""

    _app = create_app(config_file='tests/sner.yaml')
    with _app.test_request_context():
        db_remove()
        db.create_all()
        yield _app
        db_remove()


@pytest.fixture
def tmpworkdir():
    """
    self cleaning temporary workdir
    pytest tmpdir fixture has issues https://github.com/pytest-dev/pytest/issues/1120
    """

    cwd = os.getcwd()
    tmpdir = mkdtemp(prefix='sner_agent_test-')
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(cwd)
    shutil.rmtree(tmpdir)


def apikey_in_roles(roles):
    """create user apikey in role"""

    tmp_apikey = PWS.generate_apikey()
    db.session.add(User(username='pytest_user', apikey=PWS.hash_simple(tmp_apikey), active=True, roles=roles))
    db.session.commit()
    return tmp_apikey


@pytest.fixture
def apikey_agent():
    """crete user apikey agent"""

    return apikey_in_roles(['agent'])


@pytest.fixture
def apikey_user():
    """crete user apikey user"""

    return apikey_in_roles(['user'])


# auth
factoryboy_register(UserFactory)
factoryboy_register(WebauthnCredentialFactory)

# scheduler
factoryboy_register(ExclNetworkFactory, 'excl_network')
factoryboy_register(ExclRegexFactory, 'excl_regex')
factoryboy_register(JobFactory)
factoryboy_register(JobCompletedFactory, 'job_completed')
factoryboy_register(QueueFactory)
factoryboy_register(TargetFactory)

# storage
factoryboy_register(HostFactory)
factoryboy_register(NoteFactory)
factoryboy_register(ServiceFactory)
factoryboy_register(VulnFactory)
