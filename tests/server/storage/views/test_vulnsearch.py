# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.vulnsearch tests
"""

import json
from http import HTTPStatus

from flask import url_for


def test_vulnsearch_list_route(cl_operator):
    """vulnsearch list route test"""

    response = cl_operator.get(url_for('storage.vulnsearch_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_vulnsearch_list_json_route(cl_operator, vulnsearch):
    """vulnsearch list_json route test"""

    expected_cveid = vulnsearch[0].cveid

    response = cl_operator.post(
        url_for('storage.vulnsearch_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': expected_cveid}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['cveid'] == expected_cveid

    response = cl_operator.post(url_for('storage.vulnsearch_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
