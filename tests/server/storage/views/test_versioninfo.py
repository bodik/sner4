# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.versioninfo tests
"""

import json
from http import HTTPStatus

from flask import url_for


def test_versioninfo_list_route(cl_operator):
    """versioninfo list route test"""

    response = cl_operator.get(url_for('storage.versioninfo_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_versioninfo_list_json_route(cl_operator, versioninfo):
    """versioninfo list_json route test"""

    expected_product = json.loads(versioninfo[0].data)["product"].lower()

    response = cl_operator.post(
        url_for('storage.versioninfo_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': expected_product}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['product'] == expected_product

    response = cl_operator.post(
        url_for(
            'storage.versioninfo_list_json_route',
            filter=f'VersionInfo.product=="{expected_product}"',
            product=expected_product,
            versionspec='>0'
        ),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['product'] == expected_product

    response = cl_operator.post(url_for('storage.versioninfo_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
