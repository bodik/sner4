# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.portinfos tests
"""

import json
from http import HTTPStatus

from flask import url_for


def test_portinfos_route(cl_operator):
    """portinfos route test"""

    response = cl_operator.get(url_for('visuals.portinfos_route'))
    assert response.status_code == HTTPStatus.OK


def test_portinfos_json_route(cl_operator, service):
    """portinfos json route test"""

    response = cl_operator.get(url_for('visuals.portinfos_json_route'))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == service.info

    response = cl_operator.get(url_for('visuals.portinfos_json_route', crop=2, limit=1))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == ' '.join(service.info.split(' ')[:2])

    response = cl_operator.get(url_for('visuals.portinfos_json_route', filter=f'Service.port=="{service.port}"'))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == service.info

    response = cl_operator.get(url_for('visuals.portinfos_json_route', filter='invalid'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
