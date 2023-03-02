# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.dnstree tests
"""

import json
from http import HTTPStatus

from flask import url_for


def test_dnstree_route(cl_operator):
    """dnstree route test"""

    response = cl_operator.get(url_for('visuals.dnstree_route'))
    assert response.status_code == HTTPStatus.OK


def test_dnstree_json_route(cl_operator, host):
    """dnstree.json route test"""

    response = cl_operator.get(url_for('visuals.dnstree_json_route', crop=0, filter=f'Host.address=="{host.address}"'))
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert host.hostname.split('.')[0] in [tmp["name"] for tmp in response_data["nodes"]]

    response = cl_operator.get(url_for('visuals.dnstree_json_route', filter='invalid'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
