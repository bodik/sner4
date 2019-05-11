"""controller vuln tests"""

import json
from http import HTTPStatus
from random import random

from flask import url_for


from sner.server import db
from sner.server.model.storage import Vuln
from tests.server import get_csrf_token, persist_and_detach
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
	assert test_vuln.name in response_data['data'][0]['name']

	response = client.post(url_for('storage.vuln_list_json_route', filter='Vuln.name=="%s"' % test_vuln.name), {'draw': 1, 'start': 0, 'length': 1})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert test_vuln.name in response_data['data'][0]['name']


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
	form['tags'] = '\n'.join(test_vuln.tags)
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	vuln = Vuln.query.filter(Vuln.name == test_vuln.name).one_or_none()
	assert vuln
	assert vuln.xtype == test_vuln.xtype
	assert vuln.severity == test_vuln.severity
	assert vuln.refs == test_vuln.refs
	assert vuln.tags == test_vuln.tags


	db.session.delete(vuln)
	db.session.commit()


def test_vuln_edit_route(client, test_vuln):
	"""vuln edit route test"""

	test_vuln.name = 'test vuln edit %f' % random()
	persist_and_detach(test_vuln)


	form = client.get(url_for('storage.vuln_edit_route', vuln_id=test_vuln.id)).form
	form['name'] = 'edited '+form['name'].value
	form['tags'] = form['tags'].value + '\nedited'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	vuln = Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()
	assert vuln
	assert vuln.name == form['name'].value
	assert len(vuln.tags) == 3


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


def test_vuln_view_route(client, test_vuln):
	"""vuln view route test"""

	test_vuln.data = 'view%f' % random()
	test_vuln.xtype = 'nessus.vuln.testxtype'
	persist_and_detach(test_vuln)


	response = client.get(url_for('storage.vuln_view_route', vuln_id=test_vuln.id))
	assert response.status_code == HTTPStatus.OK

	assert '<pre>%s</pre>' % test_vuln.data in response


def test_delete_by_id_route(client, test_host):
	"""vuln multi delete route for ajaxed toolbars test"""

	test_vuln = create_test_vuln(test_host, None)
	test_vuln.name = 'test vuln delete by id %f' % random()
	persist_and_detach(test_vuln)


	data = {'ids-0': test_vuln.id,	'csrf_token': get_csrf_token(client)}
	response = client.post(url_for('storage.vuln_delete_by_id_route'), data)
	assert response.status_code == HTTPStatus.OK

	vuln = Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()
	assert not vuln


def test_tag_by_id_route(client, test_vuln):
	"""vuln multi tag route for ajaxed toolbars test"""

	test_vuln.name = 'test vuln tag by id %f' % random()
	persist_and_detach(test_vuln)


	data = {'tag': 'testtag', 'ids-0': test_vuln.id, 'csrf_token': get_csrf_token(client)}
	response = client.post(url_for('storage.vuln_tag_by_id_route'), data)
	assert response.status_code == HTTPStatus.OK

	vuln = Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()
	assert 'testtag' in vuln.tags


def test_vuln_grouped_route(client):
	"""vuln grouped route test"""

	response = client.get(url_for('storage.vuln_grouped_route'))
	assert response.status_code == HTTPStatus.OK
	assert '<h1>Vulns grouped' in response


def test_vuln_grouped_json_route(client, test_vuln):
	"""vuln grouped json route test"""

	test_vuln.name = 'test vuln grouped json %f' % random()
	persist_and_detach(test_vuln)

	response = client.post(url_for('storage.vuln_grouped_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_vuln.name})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert test_vuln.name in response_data['data'][0]['name']

	response = client.post(url_for('storage.vuln_grouped_json_route', filter='Vuln.name=="%s"' % test_vuln.name), {'draw': 1, 'start': 0, 'length': 1})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert test_vuln.name in response_data['data'][0]['name']
