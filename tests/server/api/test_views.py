# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api.views tests
"""

import base64
import json
from http import HTTPStatus
from ipaddress import ip_network
from pathlib import Path

from flask import current_app, url_for
from sqlalchemy import create_engine

from sner.agent import apikey_header
from sner.server.extensions import db
from sner.server.scheduler.models import Queue, Target


def test_v1_scheduler_job_assign_route(client, apikey, target):
    """job assign route test"""

    # assign from queue by name
    response = client.get(
        url_for('api.v1_scheduler_job_assign_route', queue_name=target.queue.name),
        headers=apikey_header(apikey)
    )
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)
    assert len(Queue.query.filter(Queue.name == target.queue.name).one().jobs) == 1

    # assign from non-existent queue
    response = client.get(
        url_for('api.v1_scheduler_job_assign_route', queue_id='notexist'),
        headers=apikey_header(apikey)
    )  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not json.loads(response.body.decode('utf-8'))

    # attempt without credentials
    response = client.get(url_for('api.v1_scheduler_job_assign_route'), status='*')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_v1_scheduler_job_assign_route_priority(client, apikey, queue_factory, target_factory):
    """job assign route test"""

    queue1 = queue_factory.create(name='queue1', priority=10, active=True)
    queue2 = queue_factory.create(name='queue2', priority=20, active=True)
    target_factory.create(queue=queue1)
    target_factory.create(queue=queue2)

    response = client.get(url_for('api.v1_scheduler_job_assign_route'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(json.loads(response.body.decode('utf-8')), dict)

    assert len(Queue.query.get(queue1.id).jobs) == 0
    assert len(Queue.query.get(queue2.id).jobs) == 1


def test_v1_scheduler_job_assign_route_exclusion(client, apikey, queue, excl_network, target_factory):
    """job assign route test cleaning up excluded hosts"""

    target_factory.create(queue=queue, target=str(ip_network(excl_network.value).network_address))

    response = client.get(url_for('api.v1_scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not json.loads(response.body.decode('utf-8'))


def test_v1_scheduler_job_assign_locked(client, apikey, target):  # pylint: disable=unused-argument
    """job assign route test lock handling"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(f'LOCK TABLE {Target.__tablename__} NOWAIT')

        response = client.get(url_for('api.v1_scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
        assert response.status_code == HTTPStatus.OK
        assert not json.loads(response.body.decode('utf-8'))


def test_v1_scheduler_job_output_route(client, apikey, job):
    """job output route test"""

    response = client.post_json(
        url_for('api.v1_scheduler_job_output_route'),
        {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
        headers=apikey_header(apikey)
    )
    assert response.status_code == HTTPStatus.OK

    assert job.retval == 12345
    assert Path(job.output_abspath).read_text() == 'a-test-file-contents'

    response = client.post_json(
        url_for('api.v1_scheduler_job_output_route'),
        {'invalid': 'output'},
        headers=apikey_header(apikey),
        status='*'
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
