# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage test models
"""

import pytest

from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln
from tests import persist_and_detach


def create_test_host():
    """test host data"""

    return Host(
        address='127.128.129.130',
        hostname='localhost.localdomain',
        os='some linux',
        comment='testing webserver')


def create_test_service(a_test_host):
    """test service data"""

    return Service(
        host_id=a_test_host.id,
        host=a_test_host,
        proto='tcp',
        port=22,
        state='up:syn-ack',
        name='ssh',
        info='product: OpenSSH version: 7.4p1 Debian 10+deb9u4 extrainfo: protocol 2.0 ostype: Linux',
        comment='a test service comment')


def create_test_vuln(a_test_host, a_test_service):
    """test vuln data"""

    return Vuln(
        host_id=a_test_host.id,
        host=a_test_host,
        service=(a_test_service if a_test_service else None),
        name='some vulnerability',
        xtype='scannerx.moduley',
        severity=SeverityEnum.unknown,
        descr='a vulnerability description',
        data='vuln proof',
        refs=['URL-http://localhost/ref1', 'ref2'],
        tags=['tag1', 'tag2'],
        comment='some test vuln comment')


def create_test_note(a_test_host, a_test_service):
    """test note data"""

    return Note(
        host_id=a_test_host.id,
        host=a_test_host,
        service=(a_test_service if a_test_service else None),
        xtype='testnote.xtype',
        data='test note data',
        comment='some test note comment')


@pytest.fixture
def test_host():
    """persistent test host"""

    yield persist_and_detach(create_test_host())


@pytest.fixture
def test_service(test_host):  # pylint: disable=redefined-outer-name
    """persistent test service"""

    yield persist_and_detach(create_test_service(test_host))


@pytest.fixture
def test_vuln(test_host, test_service):  # pylint: disable=redefined-outer-name
    """persistent test vuln"""

    yield persist_and_detach(create_test_vuln(test_host, test_service))


@pytest.fixture
def test_note(test_host, test_service):  # pylint: disable=redefined-outer-name
    """persistent test note"""

    yield persist_and_detach(create_test_note(test_host, test_service))
