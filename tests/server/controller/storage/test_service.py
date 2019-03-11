"""controller services tests"""

from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.storage import Service
from tests.server import persist_and_detach
from tests.server.model.storage import create_test_service


def test_service_list_route(client):
	"""service list route test"""

	response = client.get(url_for('storage.service_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Services list' in response


def test_service_add_route(client, test_host):
	"""service add route test"""

	test_service = create_test_service(test_host)
	test_service.info = 'test service add %d' % random()


	form = client.get(url_for('storage.service_add_route', host_id=test_service.host.id)).form
	form['proto'] = test_service.proto
	form['port'] = test_service.port
	form['state'] = test_service.state
	form['name'] = test_service.name
	form['info'] = test_service.info
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	service = Service.query.filter(Service.info == test_service.info).one_or_none()
	assert service
	assert service.proto == test_service.proto
	assert service.port == test_service.port
	assert service.info == test_service.info


	db.session.delete(service)
	db.session.commit()


def test_service_edit_route(client, test_service):
	"""service edit route test"""

	test_service.info = 'test service edit %d' % random()
	persist_and_detach(test_service)


	form = client.get(url_for('storage.service_edit_route', service_id=test_service.id)).form
	form['state'] = 'down'
	form['info'] = 'edited '+form['info'].value
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	service = Service.query.filter(Service.id == test_service.id).one_or_none()
	assert service
	assert service.state == form['state'].value
	assert service.info == form['info'].value


def test_service_delete_route(client, test_host):
	"""service delete route test"""

	test_service = create_test_service(test_host)
	test_service.info = 'test service delete %d' % random()
	persist_and_detach(test_service)


	form = client.get(url_for('storage.service_delete_route', service_id=test_service.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	service = Service.query.filter(Service.id == test_service.id).one_or_none()
	assert not service
