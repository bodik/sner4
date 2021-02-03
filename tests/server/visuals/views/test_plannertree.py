# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.workflowtree tests
"""

from http import HTTPStatus

import json
import yaml

from flask import current_app, url_for


def test_plannertree_route(cl_operator):
    """plannertree route test"""

    response = cl_operator.get(url_for('visuals.plannertree_route'))
    assert response.status_code == HTTPStatus.OK


def test_plannertree_json_route(cl_operator, queue_factory):
    """workflowtree.json route test"""

    queue_factory.create(name='queue1')
    queue_factory.create(name='queue2')

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
        step_groups:
          group1:
            - step: enqueue
              queue: queue2
        pipelines:
          - type: queue
            steps:
              - step: load_job
                queue: queue1
              - step: run_group
                name: group1
              - step: archive_job
          - type: queue
            steps:
              - step: load_job
                queue: queue2
              - step: import_job
              - step: archive_job
    """)

    response = cl_operator.get(url_for('visuals.plannertree_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data
