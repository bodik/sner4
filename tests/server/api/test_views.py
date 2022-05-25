# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api.views tests
"""

import base64
import json
from http import HTTPStatus
from ipaddress import ip_network
from pathlib import Path
from unittest.mock import patch

from flask import current_app, url_for
from sqlalchemy import create_engine, func, select

import sner.server.api.views
from sner.agent.core import apikey_header
from sner.server.api.schema import PublicHostSchema
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SCHEDULER_LOCK_NUMBER
from sner.server.scheduler.models import Heatmap, Job, Queue, Readynet, Target


def decode_assignment(response):
    """decode assignment from json"""
    return json.loads(response.body.decode('utf-8'))


def test_v2_scheduler_job_assign_route(client, apikey, target):
    """job assign route test"""

    qname = target.queue.name

    # assign from queue by name
    response = client.get(url_for('api.v2_scheduler_job_assign_route', queue=qname), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(decode_assignment(response), dict)
    assert len(Queue.query.filter(Queue.name == qname).one().jobs) == 1

    # assign from non-existent queue, should return response-nowork
    response = client.get(url_for('api.v2_scheduler_job_assign_route', queue='notexist'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert not decode_assignment(response)

    # attempt without credentials
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), status='*')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_v2_scheduler_job_assign_route_priority(client, apikey, queue_factory, target_factory):
    """job assign route test"""

    queue1 = queue_factory.create(name='queue1', priority=10, active=True)
    queue2 = queue_factory.create(name='queue2', priority=20, active=True)
    target_factory.create(queue=queue1)
    target_factory.create(queue=queue2)

    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assert isinstance(decode_assignment(response), dict)

    assert len(Queue.query.get(queue1.id).jobs) == 0
    assert len(Queue.query.get(queue2.id).jobs) == 1


def test_v2_scheduler_job_assign_route_exclusion(client, apikey, queue, excl_network, target_factory):
    """job assign route test cleaning up excluded hosts"""

    target_factory.create(queue=queue, target=str(ip_network(excl_network.value).network_address))

    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not decode_assignment(response)


def test_v2_scheduler_job_assign_route_locked(client, apikey, target):  # pylint: disable=unused-argument
    """job assign route test lock handling"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(select(func.pg_advisory_lock(SCHEDULER_LOCK_NUMBER)))

        with patch.object(sner.server.scheduler.core.SchedulerService, 'TIMEOUT_JOB_ASSIGN', 1):
            response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey))  # should return response-nowork

        conn.execute(select(func.pg_advisory_unlock(SCHEDULER_LOCK_NUMBER)))

    assert response.status_code == HTTPStatus.OK
    assert not decode_assignment(response)


def test_v2_scheduler_job_assign_route_caps(client, apikey, queue_factory, target_factory):  # pylint: disable=unused-argument
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
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1']})
    assert 't1' in decode_assignment(response)['targets']

    # should receive response-nowork; specific queue name request
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1'], 'queue': 'q1'})
    assert not decode_assignment(response)

    # should receive t2; q1 empty, caps match q2 reqs
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1']})
    assert 't2' in decode_assignment(response)['targets']

    # should receive t4; priority
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1', 'req2', 'req3']})
    assert 't4' in decode_assignment(response)['targets']

    # should receive t3; reqs match
    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey), params={'caps': ['req1', 'req2', 'req3']})
    assert 't3' in decode_assignment(response)['targets']


def test_v2_scheduler_job_output_route(client, apikey, job):
    """job output route test"""

    with patch.object(sner.server.scheduler.core.SchedulerService, 'HEATMAP_GC_PROBABILITY', 1.0):
        response = client.post_json(
            url_for('api.v2_scheduler_job_output_route'),
            {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
            headers=apikey_header(apikey)
        )
    assert response.status_code == HTTPStatus.OK
    assert job.retval == 12345
    assert Path(job.output_abspath).read_text(encoding='utf-8') == 'a-test-file-contents'


def test_v2_scheduler_job_output_route_invalidrequest(client, apikey):
    """job output route test invalid and discarded requests"""

    response = client.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'invalid': 'output'},
        headers=apikey_header(apikey),
        status='*'
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response = client.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retval': 1, 'output': 'invalid b64'},
        headers=apikey_header(apikey),
        status='*'
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST

    response = client.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retval': 1, 'output': ''},
        headers=apikey_header(apikey)
    )
    assert response.status_code == HTTPStatus.OK


def test_v2_scheduler_job_output_route_locked(client, apikey, job):
    """job output route test locked"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(select(func.pg_advisory_lock(SCHEDULER_LOCK_NUMBER)))

        with patch.object(sner.server.scheduler.core.SchedulerService, 'TIMEOUT_JOB_OUTPUT', 1):
            response = client.post_json(
                url_for('api.v2_scheduler_job_output_route'),
                {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
                headers=apikey_header(apikey),
                status='*'
            )

        conn.execute(select(func.pg_advisory_unlock(SCHEDULER_LOCK_NUMBER)))

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_scheduler_job_lifecycle_with_heatmap(client, apikey, queue, target_factory):
    """job assign route test"""

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 1
    target_factory.create(queue=queue, target='127.0.0.1', hashval=SchedulerService.hashval('127.0.0.1'))
    target_factory.create(queue=queue, target='127.0.0.2', hashval=SchedulerService.hashval('127.0.0.2'))

    assert len(Target.query.all()) == 2
    assert len(Readynet.query.all()) == 1
    assert len(Job.query.all()) == 0
    assert len(Heatmap.query.all()) == 0

    response = client.get(url_for('api.v2_scheduler_job_assign_route'), headers=apikey_header(apikey))
    assert response.status_code == HTTPStatus.OK
    assignment = decode_assignment(response)
    assert isinstance(assignment, dict)

    assert len(Target.query.all()) == 1
    assert len(Readynet.query.all()) == 0
    assert len(Job.query.all()) == 1
    assert len(Heatmap.query.all()) == 1

    response = client.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': assignment['id'], 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
        headers=apikey_header(apikey)
    )
    assert response.status_code == HTTPStatus.OK

    assert len(Target.query.all()) == 1
    assert len(Readynet.query.all()) == 1
    assert len(Job.query.all()) == 1


def test_v2_stats_prometheus_route(client, queue):  # pylint: disable=unused-argument
    """job prometheus stats route test"""

    response = client.get(url_for('api.v2_stats_prometheus_route'))
    assert response.status_code == HTTPStatus.OK


def test_v2_public_storage_host_route(client, apikey, host):
    """test public host api"""

    response = client.get(url_for('api.v2_public_storage_host_route', host_address=host.address), headers=apikey_header(apikey))
    assert PublicHostSchema().load(response.json)
