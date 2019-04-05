"""storage test models"""

import pytest

from sner.server import db
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln
from tests.server import persist_and_detach


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
		host=a_test_host,
		service=(a_test_service if a_test_service else None),
		name='some vulnerability',
		xtype='scannerx.moduley',
		severity=SeverityEnum.unknown,
		descr='a vulnerability description',
		data='vuln proof',
		refs=['URL-http://localhost/ref1', 'ref2'],
		comment='some test vuln comment')


def create_test_note(a_test_host):
	"""test note data"""

	return Note(
		host=a_test_host,
		ntype='testnote.ntype',
		data='test note data',
		comment='some test note comment')


@pytest.fixture()
def test_host():
	"""persistent test host"""

	tmp_host = persist_and_detach(create_test_host())
	tmp_id = tmp_host.id
	yield tmp_host
	db.session.delete(Host.query.get(tmp_id))
	db.session.commit()


@pytest.fixture()
def test_service(test_host): # pylint: disable=redefined-outer-name
	"""persistent test service"""

	tmp_service = persist_and_detach(create_test_service(test_host))
	tmp_id = tmp_service.id
	yield tmp_service
	db.session.delete(Service.query.get(tmp_id))
	db.session.commit()


@pytest.fixture()
def test_vuln(test_host, test_service): # pylint: disable=redefined-outer-name
	"""persistent test vuln"""

	tmp_vuln = persist_and_detach(create_test_vuln(test_host, test_service))
	tmp_id = tmp_vuln.id
	yield tmp_vuln
	db.session.delete(Vuln.query.get(tmp_id))
	db.session.commit()


@pytest.fixture()
def test_note(test_host): # pylint: disable=redefined-outer-name
	"""persistent test note"""

	tmp_note = persist_and_detach(create_test_note(test_host))
	tmp_id = tmp_note.id
	yield tmp_note
	db.session.delete(Note.query.get(tmp_id))
	db.session.commit()
