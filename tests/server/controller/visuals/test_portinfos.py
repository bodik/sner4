# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller portinfos tests
"""

import json
from http import HTTPStatus

from flask import url_for


def test_portinfos_route(cl_operator):
    """portinfos route test"""

    response = cl_operator.get(url_for('visuals.portinfos_route'))
    assert response.status_code == HTTPStatus.OK


def test_portinfos_json_route(cl_operator, test_service):
    """portinfos json route test"""

    response = cl_operator.get(url_for('visuals.portinfos_json_route'))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == test_service.info

    response = cl_operator.get(url_for('visuals.portinfos_json_route', crop=2, limit=1))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data[0]['info'] == ' '.join(test_service.info.split(' ')[:2])
