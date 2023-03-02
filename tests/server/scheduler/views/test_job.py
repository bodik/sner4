# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.job tests
"""

import json
from http import HTTPStatus
from pathlib import Path

from flask import url_for

from sner.server.scheduler.models import Heatmap, Job, Target


def test_job_list_route(cl_operator):
    """job list route test"""

    response = cl_operator.get(url_for('scheduler.job_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_job_list_json_route(cl_operator, job):
    """job list_json route test"""

    response = cl_operator.post(
        url_for('scheduler.job_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': job.id}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == job.id

    response = cl_operator.post(
        url_for('scheduler.job_list_json_route', filter=f'Job.id=="{job.id}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == job.id

    response = cl_operator.post(url_for('scheduler.job_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_job_delete_route(cl_operator, job_completed):
    """delete route test"""

    job_completed_id = job_completed.id
    job_completed_output_abspath = job_completed.output_abspath

    form = cl_operator.get(url_for('scheduler.job_delete_route', job_id=job_completed.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Job.query.get(job_completed_id)
    assert not Path(job_completed_output_abspath).exists()


def test_job_delete_route_runningjob(cl_operator, job):
    """job delete route test fail with running job"""

    form = cl_operator.get(url_for('scheduler.job_delete_route', job_id=job.id)).form
    response = form.submit(expect_errors=True)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    assert Job.query.get(job.id)


def test_job_reconcile_route(cl_operator, job):
    """reconcile route test"""

    assert Heatmap.query.filter(Heatmap.count > 0).count() == 2

    form = cl_operator.get(url_for('scheduler.job_reconcile_route', job_id=job.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert job.retval == -1
    assert Heatmap.query.filter(Heatmap.count > 0).count() == 0


def test_job_reconcile_completed(cl_operator, job_completed):
    """reconcile route test"""

    assert Heatmap.query.count() == 0

    form = cl_operator.get(url_for('scheduler.job_reconcile_route', job_id=job_completed.id)).form
    response = form.submit(expect_errors=True)
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    assert Heatmap.query.count() == 0


def test_job_repeat_route(cl_operator, job):
    """repeat route test"""

    form = cl_operator.get(url_for('scheduler.job_repeat_route', job_id=job.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert len(json.loads(job.assignment)['targets']) == Target.query.count()
