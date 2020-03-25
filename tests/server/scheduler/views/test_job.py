# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.job tests
"""

import json
import os
from http import HTTPStatus

from flask import url_for

from sner.server.scheduler.models import Job


def test_job_list_route(cl_operator):
    """job list route test"""

    response = cl_operator.get(url_for('scheduler.job_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_job_list_json_route(cl_operator, test_job):
    """job list_json route test"""

    response = cl_operator.post(url_for('scheduler.job_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_job.id})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == test_job.id

    response = cl_operator.post(
        url_for('scheduler.job_list_json_route', filter='Job.id=="%s"' % test_job.id),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == test_job.id


def test_job_delete_route(cl_operator, test_job_completed):
    """delete route test"""

    test_job_completed_output_abspath = Job.query.get(test_job_completed.id).output_abspath

    form = cl_operator.get(url_for('scheduler.job_delete_route', job_id=test_job_completed.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Job.query.get(test_job_completed.id)
    assert not os.path.exists(test_job_completed_output_abspath)
