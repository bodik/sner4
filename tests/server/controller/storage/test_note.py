"""controller notes tests"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.storage import Note
from tests.server.model.storage import create_test_note


def test_note_list_route(cl_operator):
    """note list route test"""

    response = cl_operator.get(url_for('storage.note_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Notes list' in response


def test_note_list_json_route(cl_operator, test_note):
    """note list_json route test"""

    response = cl_operator.post(url_for('storage.note_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_note.data})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['data'] == test_note.data

    response = cl_operator.post(
        url_for('storage.note_list_json_route', filter='Note.data=="%s"' % test_note.data),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['data'] == test_note.data


def test_note_add_route(cl_operator, test_host, test_service):
    """note add route test"""

    test_note = create_test_note(test_host, test_service)

    form = cl_operator.get(url_for('storage.note_add_route', model_name='service', model_id=test_note.service.id)).form
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


def test_note_edit_route(cl_operator, test_note):
    """note edit route test"""

    form = cl_operator.get(url_for('storage.note_edit_route', note_id=test_note.id)).form
    form['data'] = 'edited '+form['data'].value
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    note = Note.query.filter(Note.id == test_note.id).one_or_none()
    assert note
    assert note.data == form['data'].value


def test_note_delete_route(cl_operator, test_note):
    """note delete route test"""

    form = cl_operator.get(url_for('storage.note_delete_route', note_id=test_note.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    note = Note.query.filter(Note.id == test_note.id).one_or_none()
    assert not note


def test_note_view_route(cl_operator, test_note):
    """note view route test"""

    response = cl_operator.get(url_for('storage.note_view_route', note_id=test_note.id))
    assert response.status_code == HTTPStatus.OK

    assert '<dt>xtype</dt><dd>%s</dd>' % test_note.xtype in response
