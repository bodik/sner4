"""controller hosts tests"""

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
