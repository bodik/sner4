"""controller hosts tests"""

import json
from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.storage import Host
from tests.server import persist_and_detach
from tests.server.model.storage import create_test_host


def test_host_list_route(client):
	"""host list route test"""

	response = client.get(url_for('storage.host_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Hosts list' in response


def test_host_list_json_route(client, test_host):
	"""host list_json route test"""

	test_host.hostname = 'test host list json %s' % random()
	persist_and_detach(test_host)

	response = client.post(url_for('storage.host_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_host.hostname})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert response_data["data"][0]["hostname"] == test_host.hostname


def test_task_add_route(client):
	"""host add route test"""

	test_host = create_test_host()
	test_host.hostname = 'add%d.%s' % (random(), test_host.hostname)


	form = client.get(url_for('storage.host_add_route')).form
	form['address'] = test_host.address
	form['hostname'] = test_host.hostname
	form['os'] = test_host.os
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	host = Host.query.filter(Host.hostname == test_host.hostname).one_or_none()
	assert host
	assert host.hostname == test_host.hostname
	assert host.os == test_host.os


	db.session.delete(host)
	db.session.commit()


def test_host_edit_route(client, test_host):
	"""host edit route test"""

	test_host.hostname = 'edit%d.%s' % (random(), test_host.hostname)
	persist_and_detach(test_host)


	form = client.get(url_for('storage.host_edit_route', host_id=test_host.id)).form
	form['hostname'] = 'edited-'+form['hostname'].value
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	host = Host.query.filter(Host.id == test_host.id).one_or_none()
	assert host
	assert host.hostname == form['hostname'].value


def test_host_delete_route(client):
	"""host delete route test"""

	test_host = create_test_host()
	test_host.hostname = 'delete%s.%s' % (random(), test_host.hostname)
	persist_and_detach(test_host)


	form = client.get(url_for('storage.host_delete_route', host_id=test_host.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	host = Host.query.filter(Host.id == test_host.id).one_or_none()
	assert not host
