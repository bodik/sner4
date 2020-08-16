# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.workflowtree tests
"""

import json
from http import HTTPStatus

from flask import current_app, url_for


def test_workflowtree_route(cl_operator):
    """workflowtree route test"""

    response = cl_operator.get(url_for('visuals.workflowtree_route'))
    assert response.status_code == HTTPStatus.OK


def test_workflowtree_json_route(cl_operator, queue_factory):
    """workflowtree.json route test"""

    queue_factory.create(name='test queue 1')
    queue_factory.create(name='test queue 2')

    current_app.config['SNER_PLANNER'] = {
        'enqueue_servicelist': [('test queue 1', 'test queue 2')],
        'import_jobs': ['test queue 2'],
    }

    response = cl_operator.get(url_for('visuals.workflowtree_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data
