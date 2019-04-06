"""controller notes tests"""

import json
from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.storage import Note
from tests.server import persist_and_detach
from tests.server.model.storage import create_test_note


def test_note_list_route(client):
	"""note list route test"""

	response = client.get(url_for('storage.note_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert '<h1>Notes list' in response


def test_note_list_json_route(client, test_note):
	"""note list_json route test"""

	test_note.data = 'test note list json %f' % random()
	persist_and_detach(test_note)

	response = client.post(url_for('storage.note_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_note.data})
	assert response.status_code == HTTPStatus.OK
	response_data = json.loads(response.body.decode('utf-8'))
	assert response_data["data"][0]["data"] == test_note.data


def test_note_add_route(client, test_host, test_service):
	"""note add route test"""

	test_note = create_test_note(test_host, test_service)
	test_note.data = 'test note add %f' % random()


	form = client.get(url_for('storage.note_add_route', model_name='service', model_id=test_note.service.id)).form
	form['xtype'] = test_note.xtype
	form['data'] = test_note.data
	form['comment'] = test_note.comment
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	note = Note.query.filter(Note.data == test_note.data).one_or_none()
	assert note
	assert note.xtype == test_note.xtype
	assert note.data == test_note.data
	assert note.comment == test_note.comment


	db.session.delete(note)
	db.session.commit()


def test_note_edit_route(client, test_note):
	"""note edit route test"""

	test_note.data = 'test note edit %f' % random()
	persist_and_detach(test_note)


	form = client.get(url_for('storage.note_edit_route', note_id=test_note.id)).form
	form['data'] = 'edited '+form['data'].value
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	note = Note.query.filter(Note.id == test_note.id).one_or_none()
	assert note
	assert note.data == form['data'].value


def test_note_delete_route(client, test_host):
	"""note delete route test"""

	test_note = create_test_note(test_host, None)
	test_note.data = 'test note delete %f' % random()
	persist_and_detach(test_note)


	form = client.get(url_for('storage.note_delete_route', note_id=test_note.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	note = Note.query.filter(Note.id == test_note.id).one_or_none()
	assert not note


def test_note_view_route(client, test_note):
	"""note view route test"""

	test_note.data = 'view%f' % random()
	test_note.xtype = 'nessus.note.testxtype'
	persist_and_detach(test_note)


	response = client.get(url_for('storage.note_view_route', note_id=test_note.id))
	assert response.status_code == HTTPStatus.OK

	assert '<pre>%s</pre>' % test_note.data in response
