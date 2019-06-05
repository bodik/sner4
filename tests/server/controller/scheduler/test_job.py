"""controller job tests"""

import base64
import json
import os
from http import HTTPStatus

from flask import url_for

from sner.server.model.scheduler import Job, Queue
from tests import persist_and_detach
from tests.server.model.scheduler import create_test_target


def test_job_list_route(client):
    """job list route test"""

    response = client.get(url_for('scheduler.job_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Jobs list' in response


def test_job_list_json_route(client, test_job):
    """job list_json route test"""

    response = client.post(url_for('scheduler.job_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_job.id})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == test_job.id

    response = client.post(
        url_for('scheduler.job_list_json_route', filter='Job.id=="%s"' % test_job.id),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['id'] == test_job.id


def test_job_assign_route(client, test_queue):
    """job assign route test"""

    persist_and_detach(create_test_target(test_queue))
    response = client.get(url_for('scheduler.job_assign_route', queue_id=test_queue.id))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)
    queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
    assert len(queue.jobs) == 1

    persist_and_detach(create_test_target(test_queue))
    response = client.get(url_for('scheduler.job_assign_route', queue_id=test_queue.name))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)
    queue = Queue.query.filter(Queue.name == test_queue.name).one_or_none()
    assert len(queue.jobs) == 2


def test_job_assign_highest_priority_route(client, test_task):
    """job assign route test"""

    queue1 = Queue(name='queue1', task=test_task, group_size=1, priority=10, active=True)
    persist_and_detach(queue1)
    queue2 = Queue(name='queue2', task=test_task, group_size=1, priority=20, active=True)
    persist_and_detach(queue2)
    persist_and_detach(create_test_target(queue1))
    persist_and_detach(create_test_target(queue2))

    response = client.get(url_for('scheduler.job_assign_route'))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)

    queue = Queue.query.filter(Queue.id == queue1.id).one_or_none()
    assert len(queue.jobs) == 0
    queue = Queue.query.filter(Queue.id == queue2.id).one_or_none()
    assert len(queue.jobs) == 1


def test_job_output_route(client, test_job):
    """job output route test"""

    response = client.post_json(
        url_for('scheduler.job_output_route'),
        {'id': test_job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')})
    assert response.status_code == HTTPStatus.OK

    job = Job.query.filter(Job.id == test_job.id).one_or_none()
    assert job.retval == 12345
    with open(job.output_abspath, 'r') as ftmp:
        assert ftmp.read() == 'a-test-file-contents'

    response = client.post_json(url_for('scheduler.job_output_route'), {'invalid': 'output'}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_job_delete_route(client, test_job_completed):
    """delete route test"""

    form = client.get(url_for('scheduler.job_delete_route', job_id=test_job_completed.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    job = Job.query.filter(Job.id == test_job_completed.id).one_or_none()
    assert not job
    assert not os.path.exists(test_job_completed.output_abspath)
