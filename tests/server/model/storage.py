"""storage test models"""

import pytest

from sner.server import db
from sner.server.model.storage import Host, Service
from tests.server import persist_and_detach


def create_test_host():
	"""test host data"""

	return Host(
		address='127.128.129.130',
		hostname='localhost.localdomain',
		os='some linux')


def create_test_service(a_test_host):
	"""test service data"""

	return Service(
		host=a_test_host,
		proto='tcp',
		port=22,
		state='up:syn-ack',
		name='ssh',
		info='product: OpenSSH version: 7.4p1 Debian 10+deb9u4 extrainfo: protocol 2.0 ostype: Linux')


@pytest.fixture()
def test_host():
	"""persistent test host"""

	tmp_host = persist_and_detach(create_test_host())
	tmp_id = tmp_host.id
	yield tmp_host
	db.session.delete(Host.query.get(tmp_id))
	db.session.commit()


@pytest.fixture()
def test_service(test_host):
	"""persistent test service"""

	tmp_service = persist_and_detach(create_test_service(test_host))
	tmp_id = tmp_service.id
	yield tmp_service
	db.session.delete(Service.query.get(tmp_id))
	db.session.commit()
