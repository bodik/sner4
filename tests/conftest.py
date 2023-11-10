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
from sner.server.extensions import db
from sner.server.dbx_command import db_remove
from sner.server.password_supervisor import PasswordSupervisor as PWS
from sner.server.storage.models import VersionInfo
from sner.server.storage.versioninfo import VersionInfoManager
from tests.server.auth.models import UserFactory, WebauthnCredentialFactory
from tests.server.scheduler.models import (
    JobFactory,
    JobCompletedFactory,
    QueueFactory,
    TargetFactory
)
from tests.server.storage.models import HostFactory, NoteFactory, ServiceFactory, VulnFactory, VulnsearchFactory


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


def apikey_in_roles(ufactory, roles):
    """create user apikey in role"""

    tmp_apikey = PWS.generate_apikey()
    ufactory.create(username='pytest_user', apikey=PWS.hash_simple(tmp_apikey), roles=roles)
    return tmp_apikey


@pytest.fixture
def apikey_agent(user_factory):
    """crete user apikey agent"""

    return apikey_in_roles(user_factory, ['agent'])


@pytest.fixture
def apikey_user(user_factory):
    """crete user apikey user"""

    return apikey_in_roles(user_factory, ['user'])


# auth
factoryboy_register(UserFactory)
factoryboy_register(WebauthnCredentialFactory)

# scheduler
factoryboy_register(JobFactory)
factoryboy_register(JobCompletedFactory, 'job_completed')
factoryboy_register(QueueFactory)
factoryboy_register(TargetFactory)

# storage
factoryboy_register(HostFactory)
factoryboy_register(NoteFactory)
factoryboy_register(ServiceFactory)
factoryboy_register(VulnFactory)
factoryboy_register(VulnsearchFactory, 'vulnsearch_dangling')


@pytest.fixture
def versioninfo_notes(host, service_factory, note_factory):
    """prepare notes for versioninfo map generation"""

    yield [
        note_factory.create(
            host=host,
            service=service_factory.create(
                host=host,
                port=80,
                name='http',
                info='product: Apache httpd version: 2.2.21 extrainfo: (Win32) mod_ssl/2.2.21 OpenSSL/1.0.0e PHP/5.3.8 mod_perl/2.0.4 Perl/v5.10.1',
            ),
            xtype='nmap.banner_dict',
            data='{"product": "Apache httpd", "version": "2.2.21", '
                 '"extrainfo": "(Win32) mod_ssl/2.2.21 OpenSSL/1.0.0e PHP/5.3.8 mod_perl/2.0.4 Perl/v5.10.1"}'
        ),
        note_factory.create(
            host=host,
            service=service_factory.create(
                host=host,
                port=15002,
                name='pbs-maui',
                info='product: PBS/Maui Roll extrainfo: Rocks Cluster devicetype: specialized',
            ),
            xtype='nmap.banner_dict',
            data='{"product": "PBS/Maui Roll", "extrainfo": "Rocks Cluster", "devicetype": "specialized"}'
        ),
        note_factory.create(
            host=host,
            service=service_factory.create(
                host=host,
                port=111,
                name='rpcbind',
                info='version: 2-4 extrainfo: RPC #100000',
            ),
            xtype='nmap.banner_dict',
            data='{"version": "2-4", "extrainfo": "RPC #100000"}'
        )
    ]


@pytest.fixture
def versioninfos(versioninfo_notes):  # pylint: disable=redefined-outer-name,unused-argument
    """prepare versioninfo map snap"""

    VersionInfoManager.rebuild()
    return VersionInfo.query.all()


@pytest.fixture
def vulnsearch(service, vulnsearch_factory):
    """
    prepare vulnsearch

    factory_boy cannot create model with multiple related subfactories, hence
    the "proper" vulnsearch generation is done here by hand
    """

    yield vulnsearch_factory(
        host_id=service.host.id,
        service_id=service.id,
        host_address=service.host.address,
        host_hostname=service.host.hostname,
        service_proto=service.proto,
        service_port=service.port
    )
