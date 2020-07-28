# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.workflowtree tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.utils import yaml_dump


def test_workflowtree_route(cl_operator):
    """workflowtree route test"""

    response = cl_operator.get(url_for('visuals.workflowtree_route'))
    assert response.status_code == HTTPStatus.OK


def test_workflowtree_json_route(cl_operator, queue_factory):
    """workflowtree.json route test"""

    queue_factory.create(name='test queue 1', workflow=yaml_dump({'step': 'enqueue_servicelist', 'queue': 'test queue 2'}))
    queue_factory.create(name='test queue 2', workflow=yaml_dump({'step': 'import'}))

    response = cl_operator.get(url_for('visuals.workflowtree_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data
