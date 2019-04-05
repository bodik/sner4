"""controller vuln tests"""

import json
from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.storage import Vuln
from tests.server import persist_and_detach
from tests.server.model.storage import create_test_vuln


def test_vuln_list_route(client):
	"""vuln list route test"""

	response = client.get(url_for('storage.vuln_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert '<h1>Vulns list' in response


def test_vuln_list_json_route(client, test_vuln):
	"""vuln list_json route test"""

	test_vuln.name = 'test vuln list json %f' % random()
	persist_and_detach(test_vuln)

	response = client.post(url_for('storage.vuln_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_vuln.name})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert response_data['data'][0]['name'] == test_vuln.name


def test_vuln_add_route(client, test_host, test_service):
	"""vuln add route test"""

	test_vuln = create_test_vuln(test_host, test_service)
	test_vuln.name = 'test vuln add %f' % random()


	form = client.get(url_for('storage.vuln_add_route', model_name='service', model_id=test_vuln.service.id)).form
	form['name'] = test_vuln.name
	form['xtype'] = test_vuln.xtype
	form['severity'] = str(test_vuln.severity)
	form['descr'] = test_vuln.descr
	form['data'] = test_vuln.descr
	form['refs'] = '\n'.join(test_vuln.refs)
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	vuln = Vuln.query.filter(Vuln.name == test_vuln.name).one_or_none()
	assert vuln
	assert vuln.xtype == test_vuln.xtype
	assert vuln.severity == test_vuln.severity
	assert vuln.refs == test_vuln.refs


	db.session.delete(vuln)
	db.session.commit()


def test_vuln_edit_route(client, test_vuln):
	"""vuln edit route test"""

	test_vuln.name = 'test vuln edit %f' % random()
	persist_and_detach(test_vuln)


	form = client.get(url_for('storage.vuln_edit_route', vuln_id=test_vuln.id)).form
	form['name'] = 'edited '+form['name'].value
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	vuln = Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()
	assert vuln
	assert vuln.name == form['name'].value


def test_vuln_delete_route(client, test_host):
	"""vuln delete route test"""

	test_vuln = create_test_vuln(test_host, None)
	test_vuln.name = 'test vuln delete %f' % random()
	persist_and_detach(test_vuln)


	form = client.get(url_for('storage.vuln_delete_route', vuln_id=test_vuln.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	vuln = Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()
	assert not vuln
