# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller services tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.storage import Service
from tests.server.model.storage import create_test_service


def test_service_list_route(cl_operator):
    """service list route test"""

    response = cl_operator.get(url_for('storage.service_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_service_list_json_route(cl_operator, test_service):
    """service list_json route test"""

    response = cl_operator.post(url_for('storage.service_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_service.info})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == test_service.info

    response = cl_operator.post(
        url_for('storage.service_list_json_route', filter='Service.info=="%s"' % test_service.info),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == test_service.info


def test_service_add_route(cl_operator, test_host):
    """service add route test"""

    test_service = create_test_service(test_host)

    form = cl_operator.get(url_for('storage.service_add_route', host_id=test_service.host.id)).form
    form['proto'] = test_service.proto
    form['port'] = test_service.port
    form['state'] = test_service.state
    form['name'] = test_service.name
    form['info'] = test_service.info
    form['comment'] = test_service.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    service = Service.query.filter(Service.info == test_service.info).one_or_none()
    assert service
    assert service.proto == test_service.proto
    assert service.port == test_service.port
    assert service.info == test_service.info
    assert service.comment == test_service.comment


def test_service_edit_route(cl_operator, test_service):
    """service edit route test"""

    form = cl_operator.get(url_for('storage.service_edit_route', service_id=test_service.id)).form
    form['state'] = 'down'
    form['info'] = 'edited '+form['info'].value
    form['return_url'] = url_for('storage.service_list_route')
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    service = Service.query.filter(Service.id == test_service.id).one_or_none()
    assert service
    assert service.state == form['state'].value
    assert service.info == form['info'].value


def test_service_delete_route(cl_operator, test_service):
    """service delete route test"""

    form = cl_operator.get(url_for('storage.service_delete_route', service_id=test_service.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    service = Service.query.filter(Service.id == test_service.id).one_or_none()
    assert not service


def test_service_grouped_route(cl_operator):
    """service grouped route test"""

    response = cl_operator.get(url_for('storage.service_grouped_route'))
    assert response.status_code == HTTPStatus.OK


def test_service_grouped_json_route(cl_operator, test_service):
    """service grouped json route test"""

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_service.info})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_service.info in response_data['data'][0]['info']

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route', filter='Service.info=="%s"' % test_service.info),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_service.info in response_data['data'][0]['info']

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route', crop=2),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == ' '.join(test_service.info.split(' ')[:2])


def test_service_vizinfos_route(cl_operator):
    """service vizinfos route test"""

    response = cl_operator.get(url_for('storage.service_vizinfos_route'))
    assert response.status_code == HTTPStatus.OK


def test_service_vizinfos_json_route(cl_operator, test_service):
    """service vizinfos json route test"""

    response = cl_operator.get(url_for('storage.service_vizinfos_json_route'))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == test_service.info

    response = cl_operator.get(url_for('storage.service_vizinfos_json_route', crop=2, limit=1))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == ' '.join(test_service.info.split(' ')[:2])
