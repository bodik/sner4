# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.service tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.storage.models import Service
from tests.server.storage.views import check_annotate


def test_service_list_route(cl_operator):
    """service list route test"""

    response = cl_operator.get(url_for('storage.service_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_service_list_json_route(cl_operator, service):
    """service list_json route test"""

    response = cl_operator.post(url_for('storage.service_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': service.info})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == service.info

    response = cl_operator.post(
        url_for('storage.service_list_json_route', filter=f'Service.info=="{service.info}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == service.info

    # test filtering library for joined models handling
    response = cl_operator.post(
        url_for('storage.service_list_json_route', filter=f'Host.address=="{service.host.address}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK


def test_service_add_route(cl_operator, host, service_factory):
    """service add route test"""

    aservice = service_factory.build(host=host)

    form = cl_operator.get(url_for('storage.service_add_route', host_id=aservice.host.id)).forms['service_form']
    form['proto'] = aservice.proto
    form['port'] = aservice.port
    form['state'] = aservice.state
    form['name'] = aservice.name
    form['info'] = aservice.info
    form['comment'] = aservice.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tservice = Service.query.filter(Service.info == aservice.info).one()
    assert tservice.proto == aservice.proto
    assert tservice.port == aservice.port
    assert tservice.info == aservice.info
    assert tservice.comment == aservice.comment


def test_service_edit_route(cl_operator, service):
    """service edit route test"""

    form = cl_operator.get(url_for('storage.service_edit_route', service_id=service.id)).forms['service_form']
    form['state'] = 'down'
    form['info'] = 'edited ' + form['info'].value
    form['return_url'] = url_for('storage.service_list_route')
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tservice = Service.query.get(service.id)
    assert tservice.state == form['state'].value
    assert tservice.info == form['info'].value


def test_service_delete_route(cl_operator, service):
    """service delete route test"""

    form = cl_operator.get(url_for('storage.service_delete_route', service_id=service.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Service.query.get(service.id)


def test_service_annotate_route(cl_operator, service):
    """service annotate route test"""

    check_annotate(cl_operator, 'storage.service_annotate_route', service)


def test_service_grouped_route(cl_operator):
    """service grouped route test"""

    response = cl_operator.get(url_for('storage.service_grouped_route'))
    assert response.status_code == HTTPStatus.OK


def test_service_grouped_json_route(cl_operator, service):
    """service grouped json route test"""

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': service.info}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert service.info in response_data['data'][0]['info']

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route', filter=f'Service.info=="{service.info}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert service.info in response_data['data'][0]['info']

    response = cl_operator.post(
        url_for('storage.service_grouped_json_route', crop=2),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['info'] == ' '.join(service.info.split(' ')[:2])
