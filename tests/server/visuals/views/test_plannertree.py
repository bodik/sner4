# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.workflowtree tests
"""

import json
from http import HTTPStatus

from flask import current_app, url_for


def test_plannertree_route(cl_operator):
    """plannertree route test"""

    response = cl_operator.get(url_for('visuals.plannertree_route'))
    assert response.status_code == HTTPStatus.OK


def test_plannertree_json_route(cl_operator, queue_factory):
    """workflowtree.json route test"""

    queue_factory.create(name='test queue 1')
    queue_factory.create(name='test queue 2')

    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'name': 'test1',
            'type': 'queue',
            'steps': [
                {'step': 'load_job', 'queue': 'test queue 1'},
                {'step': 'enqueue', 'queue': 'test queue 2'},
                {'step': 'archive_job'},
            ]
        },
        {
            'name': 'test2',
            'type': 'queue',
            'steps': [
                {'step': 'load_job', 'queue': 'test queue 2'},
                {'step': 'import_job'},
                {'step': 'archive_job'}
                # break pylint duplicate-code
            ]
        }
    ]

    response = cl_operator.get(url_for('visuals.plannertree_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data
