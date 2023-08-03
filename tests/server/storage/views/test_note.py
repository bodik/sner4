# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.note tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.storage.models import Note
from tests.server.storage.views import check_annotate, check_delete_multiid, check_tag_multiid


def test_note_list_route(cl_operator):
    """note list route test"""

    response = cl_operator.get(url_for('storage.note_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_note_list_json_route(cl_operator, note):
    """note list_json route test"""

    response = cl_operator.post(url_for('storage.note_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': note.data})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['data'] == note.data

    response = cl_operator.post(
        url_for('storage.note_list_json_route', filter=f'Note.data=="{note.data}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['data'] == note.data

    response = cl_operator.post(url_for('storage.note_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_note_add_route(cl_operator, host, service, note_factory):
    """note add route test"""

    anote = note_factory.build(host=host, service=service)

    form = cl_operator.get(url_for('storage.note_add_route', model_name='service', model_id=anote.service.id)).forms['note_form']
    form['xtype'] = anote.xtype
    form['data'] = anote.data
    form['comment'] = anote.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tnote = Note.query.filter(Note.data == anote.data).one()
    assert tnote.xtype == anote.xtype
    assert tnote.data == anote.data
    assert tnote.comment == anote.comment


def test_note_edit_route(cl_operator, note):
    """note edit route test"""

    form = cl_operator.get(url_for('storage.note_edit_route', note_id=note.id)).forms['note_form']
    form['data'] = 'edited ' + form['data'].value
    form['return_url'] = url_for('storage.note_list_route')
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tnote = Note.query.get(note.id)
    assert tnote.data == form['data'].value


def test_note_delete_route(cl_operator, note):
    """note delete route test"""

    form = cl_operator.get(url_for('storage.note_delete_route', note_id=note.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Note.query.get(note.id)


def test_note_annotate_route(cl_operator, note):
    """note annotate route test"""

    check_annotate(cl_operator, 'storage.note_annotate_route', note)


def test_note_tag_multiid_route(cl_operator, note):
    """note tag_multiid route test"""

    check_tag_multiid(cl_operator, 'storage.note_tag_multiid_route', note)


def test_note_delete_multiid_route(cl_operator, note):
    """note delete_multiid route test"""

    check_delete_multiid(cl_operator, 'storage.note_delete_multiid_route', note)


def test_note_view_route(cl_operator, note):
    """note view route test"""

    response = cl_operator.get(url_for('storage.note_view_route', note_id=note.id))
    assert response.status_code == HTTPStatus.OK
