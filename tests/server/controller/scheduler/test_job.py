"""controller job tests"""

import base64
import json
from http import HTTPStatus

from flask import url_for

from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job, Queue


def test_job_list_route(client):
    """job list route test"""

    response = client.get(url_for('scheduler.job_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Jobs list' in response


def test_job_assign_route(client, test_target):
    """job assign route test"""

    test_queue_id = test_target.queue_id

    response = client.get(url_for('scheduler.job_assign_route', queue_id=test_queue_id))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)

    queue = Queue.query.filter(Queue.id == test_queue_id).one_or_none()
    assert len(queue.jobs) == 1


def test_job_output_route(client, test_job):
    """job output route test"""

    response = client.post_json(
        url_for('scheduler.job_output_route'),
        {'id': test_job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')})
    assert response.status_code == HTTPStatus.OK

    job = Job.query.filter(Job.id == test_job.id).one_or_none()
    assert job.retval == 12345
    with open(job_output_filename(test_job.id), 'r') as ftmp:
        assert ftmp.read() == 'a-test-file-contents'


def test_job_delete_route(client, test_job):
    """delete route test"""

    form = client.get(url_for('scheduler.job_delete_route', job_id=test_job.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    job = Job.query.filter(Job.id == test_job.id).one_or_none()
    assert not job
