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
from sner.server.db_command import db_remove
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server.auth.models import UserFactory, WebauthnCredentialFactory
from tests.server.scheduler.models import (
    ExclNetworkFactory,
    ExclRegexFactory,
    JobFactory,
    JobCompletedFactory,
    QueueFactory,
    TaskFactory,
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


@pytest.fixture
def apikey():
    """yield valid apikey for user in role agent"""

    tmp_apikey = PWS().generate_apikey()
    db.session.add(User(username='pytest_agent', apikey=tmp_apikey, active=True, roles=['agent']))
    db.session.commit()
    yield tmp_apikey


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
factoryboy_register(TaskFactory)

# storage
factoryboy_register(HostFactory)
factoryboy_register(NoteFactory)
factoryboy_register(ServiceFactory)
factoryboy_register(VulnFactory)
