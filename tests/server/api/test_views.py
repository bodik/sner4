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

from sner.agent.core import apikey_header
from sner.server.extensions import db
from sner.server.scheduler.models import Queue, Target


def decode_assignment(response):
    """decode assignment from json"""
    return json.loads(response.body.decode('utf-8'))


def test_scheduler_job_assign_route(client, apikey, target):
    """job assign route test"""

    qname = target.queue.name

    # assign from queue by name
    response = client.get(url_for('api.scheduler_job_assign_route', queue=qname), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(decode_assignment(response), dict)
    assert len(Queue.query.filter(Queue.name == qname).one().jobs) == 1

    # assign from non-existent queue, should return response-nowork
    response = client.get(url_for('api.scheduler_job_assign_route', queue='notexist'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert not decode_assignment(response)

    # attempt without credentials
    response = client.get(url_for('api.scheduler_job_assign_route'), status='*')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_scheduler_job_assign_route_priority(client, apikey, queue_factory, target_factory):
    """job assign route test"""

    queue1 = queue_factory.create(name='queue1', priority=10, active=True)
    queue2 = queue_factory.create(name='queue2', priority=20, active=True)
    target_factory.create(queue=queue1)
    target_factory.create(queue=queue2)

    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(decode_assignment(response), dict)

    assert len(Queue.query.get(queue1.id).jobs) == 0
    assert len(Queue.query.get(queue2.id).jobs) == 1


def test_scheduler_job_assign_route_exclusion(client, apikey, queue, excl_network, target_factory):
    """job assign route test cleaning up excluded hosts"""

    target_factory.create(queue=queue, target=str(ip_network(excl_network.value).network_address))

    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not decode_assignment(response)


def test_scheduler_job_assign_route_locked(client, apikey, target):  # pylint: disable=unused-argument
    """job assign route test lock handling"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(f'LOCK TABLE {Target.__tablename__} NOWAIT')

        response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
        assert response.status_code == HTTPStatus.OK
        assert not decode_assignment(response)


def test_scheduler_job_assign_route_caps(client, apikey, queue_factory, target_factory):  # pylint: disable=unused-argument
    """test assignment with client capabilities"""

    queue1 = queue_factory.create(name='q1', priority=20)
    queue2 = queue_factory.create(name='q2', reqs=['req1'], priority=10)
    queue3 = queue_factory.create(name='q3', reqs=['req1', 'req2'], priority=10)
    queue4 = queue_factory.create(name='q4', reqs=['req1', 'req2'], priority=30)

    target_factory.create(queue=queue1, target='t1')
    target_factory.create(queue=queue2, target='t2')
    target_factory.create(queue=queue3, target='t3')
    target_factory.create(queue=queue4, target='t4')

    # should receive t1; priority
    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1']})
    assert 't1' in decode_assignment(response)['targets']

    # should receive response-nowork; specific queue name request
    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1'], 'queue': 'q1'})
    assert not decode_assignment(response)

    # should receive t2; q1 empty, caps match q2 reqs
    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1']})
    assert 't2' in decode_assignment(response)['targets']

    # should receive t4; priority
    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1', 'req2', 'req3']})
    assert 't4' in decode_assignment(response)['targets']

    # should receive t3; reqs match
    response = client.get(url_for('api.scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1', 'req2', 'req3']})
    assert 't3' in decode_assignment(response)['targets']


def test_scheduler_job_output_route(client, apikey, job):
    """job output route test"""

    response = client.post_json(
        url_for('api.scheduler_job_output_route'),
        {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
        headers=apikey_header(apikey)
    )
    assert response.status_code == HTTPStatus.OK

    assert job.retval == 12345
    assert Path(job.output_abspath).read_text(encoding='utf-8') == 'a-test-file-contents'

    response = client.post_json(
        url_for('api.scheduler_job_output_route'),
        {'invalid': 'output'},
        headers=apikey_header(apikey),
        status='*'
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_stats_prometheus_route(client, queue):  # pylint: disable=unused-argument
    """job prometheus stats route test"""

    response = client.get(url_for('api.stats_prometheus_route'))
    assert response.status_code == HTTPStatus.OK
