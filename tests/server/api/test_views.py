# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api.views tests
"""

import base64
import json
from http import HTTPStatus
from ipaddress import ip_network

from flask import url_for

from sner.agent import apikey_header
from sner.server.scheduler.models import Job, Queue, Target
from tests import persist_and_detach
from tests.server.scheduler.models import create_test_target


def test_v1_scheduler_job_assign_route(client, apikey, test_queue):
    """job assign route test"""

    # assign from queue by id
    persist_and_detach(create_test_target(test_queue))
    response = client.get(url_for('api.v1_scheduler_job_assign_route', queue_ident=test_queue.id), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)
    assert len(Queue.query.get(test_queue.id).jobs) == 1

    # assign from queue by name
    persist_and_detach(create_test_target(test_queue))
    response = client.get(url_for('api.v1_scheduler_job_assign_route', queue_ident=test_queue.ident), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)
    assert len(Queue.query.filter(Queue.ident == test_queue.ident).one().jobs) == 2

    # assign from non-existent queue
    response = client.get(
        url_for('api.v1_scheduler_job_assign_route', queue_id='notexist'),
        headers=apikey_header(apikey))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not json.loads(response.body.decode('utf-8'))

    # attempt without credentials
    response = client.get(url_for('api.v1_scheduler_job_assign_route'), status='*')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_v1_scheduler_job_assign_route_priority(client, apikey, test_task):
    """job assign route test"""

    queue1 = Queue(name='queue1', task=test_task, priority=10, active=True)
    persist_and_detach(queue1)
    queue2 = Queue(name='queue2', task=test_task, priority=20, active=True)
    persist_and_detach(queue2)
    persist_and_detach(create_test_target(queue1))
    persist_and_detach(create_test_target(queue2))

    response = client.get(url_for('api.v1_scheduler_job_assign_route'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)

    assert len(Queue.query.get(queue1.id).jobs) == 0
    assert len(Queue.query.get(queue2.id).jobs) == 1


def test_v1_scheduler_job_assign_route_exclusion(client, apikey, test_queue, test_excl_network):
    """job assign route test cleaning up excluded hosts"""

    persist_and_detach(Target(target=str(ip_network(test_excl_network.value).network_address), queue=test_queue))
    response = client.get(url_for('api.v1_scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not json.loads(response.body.decode('utf-8'))


def test_v1_scheduler_job_output_route(client, apikey, test_job):
    """job output route test"""

    response = client.post_json(
        url_for('api.v1_scheduler_job_output_route'),
        {'id': test_job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
        headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK

    job = Job.query.get(test_job.id)
    assert job.retval == 12345
    with open(job.output_abspath, 'r') as ftmp:
        assert ftmp.read() == 'a-test-file-contents'

    response = client.post_json(url_for('api.v1_scheduler_job_output_route'), {'invalid': 'output'}, headers=apikey_header(apikey), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
