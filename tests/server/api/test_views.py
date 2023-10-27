# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api.views tests
"""

import base64
from http import HTTPStatus
from ipaddress import ip_network
from pathlib import Path
from unittest.mock import patch

from flask import current_app, url_for
from sqlalchemy import create_engine, func, select

import sner.server.api.views
import sner.server.api.schema as api_schema
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SCHEDULER_LOCK_NUMBER
from sner.server.scheduler.models import Heatmap, Job, Queue, Readynet, Target


def test_v2_scheduler_job_assign_route(client, api_agent, target):
    """job assign route test"""

    qname = target.queue.name

    # assign from queue by name
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'queue': qname})
    assert response.status_code == HTTPStatus.OK
    assert response.json
    assert len(Queue.query.filter(Queue.name == qname).one().jobs) == 1

    # assign from non-existent queue, should return response-nowork
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'queue': 'notexist'})
    assert response.status_code == HTTPStatus.OK
    assert not response.json

    # attempt without credentials
    response = client.post_json(url_for('api.v2_scheduler_job_assign_route'), status='*')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_v2_scheduler_job_assign_route_maintenance(api_agent, target):
    """job assign route test maintenance test"""

    qname = target.queue.name

    # test maintenance
    current_app.config['SNER_MAINTENANCE'] = True
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'queue': qname})
    assert response.status_code == HTTPStatus.OK
    assert not response.json

    current_app.config['SNER_MAINTENANCE'] = False
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'queue': qname})
    assert response.status_code == HTTPStatus.OK
    assert response.json
    assert len(Queue.query.filter(Queue.name == qname).one().jobs) == 1


def test_v2_scheduler_job_assign_route_priority(api_agent, queue_factory, target_factory):
    """job assign route test"""

    queue1 = queue_factory.create(name='queue1', priority=10, active=True)
    queue2 = queue_factory.create(name='queue2', priority=20, active=True)
    target_factory.create(queue=queue1)
    target_factory.create(queue=queue2)

    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'))
    assert response.status_code == HTTPStatus.OK
    assert response.json

    assert len(Queue.query.get(queue1.id).jobs) == 0
    assert len(Queue.query.get(queue2.id).jobs) == 1


def test_v2_scheduler_job_assign_route_exclusion(api_agent, queue, target_factory):
    """job assign route test cleaning up excluded hosts"""

    current_app.config['SNER_EXCLUSIONS'] = [['network', '127.66.66.0/24']]
    target_factory.create(queue=queue, target=str(ip_network(current_app.config['SNER_EXCLUSIONS'][0][1]).network_address))

    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'))  # should return response-nowork
    assert response.status_code == HTTPStatus.OK
    assert not response.json


def test_v2_scheduler_job_assign_route_locked(api_agent, target):  # pylint: disable=unused-argument
    """job assign route test lock handling"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(select(func.pg_advisory_lock(SCHEDULER_LOCK_NUMBER)))

        with patch.object(sner.server.scheduler.core.SchedulerService, 'TIMEOUT_JOB_ASSIGN', 1):
            response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'))  # should return response-nowork

        conn.execute(select(func.pg_advisory_unlock(SCHEDULER_LOCK_NUMBER)))

    assert response.status_code == HTTPStatus.OK
    assert not response.json


def test_v2_scheduler_job_assign_route_caps(api_agent, queue_factory, target_factory):  # pylint: disable=unused-argument
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
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'caps': ['req1']})
    assert 't1' in response.json['targets']

    # should receive response-nowork; specific queue name request
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'caps': ['req1'], 'queue': 'q1'})
    assert not response.json

    # should receive t2; q1 empty, caps match q2 reqs
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'caps': ['req1']})
    assert 't2' in response.json['targets']

    # should receive t4; priority
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'caps': ['req1', 'req2', 'req3']})
    assert 't4' in response.json['targets']

    # should receive t3; reqs match
    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'), {'caps': ['req1', 'req2', 'req3']})
    assert 't3' in response.json['targets']


def test_v2_scheduler_job_output_route(api_agent, job):
    """job output route test"""

    with patch.object(sner.server.scheduler.core.SchedulerService, 'HEATMAP_GC_PROBABILITY', 1.0):
        response = api_agent.post_json(
            url_for('api.v2_scheduler_job_output_route'),
            {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')}
        )
    assert response.status_code == HTTPStatus.OK
    assert job.retval == 12345
    assert Path(job.output_abspath).read_text(encoding='utf-8') == 'a-test-file-contents'


def test_v2_scheduler_job_output_route_invalidrequest(api_agent):
    """job output route test invalid and discarded requests"""

    response = api_agent.post_json(url_for('api.v2_scheduler_job_output_route'), {'invalid': 'output'}, status='*')
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    response = api_agent.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retval': 1, 'output': 'invalid b64'},
        status='*'
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST

    response = api_agent.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'retval': 1, 'output': ''}
    )
    assert response.status_code == HTTPStatus.OK


def test_v2_scheduler_job_output_route_locked(api_agent, job):
    """job output route test locked"""

    # flush current session and create new independent connection to simulate lock from other agent
    db.session.commit()
    with create_engine(current_app.config['SQLALCHEMY_DATABASE_URI']).connect() as conn:
        conn.execute(select(func.pg_advisory_lock(SCHEDULER_LOCK_NUMBER)))

        with patch.object(sner.server.scheduler.core.SchedulerService, 'TIMEOUT_JOB_OUTPUT', 1):
            response = api_agent.post_json(
                url_for('api.v2_scheduler_job_output_route'),
                {'id': job.id, 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
                status='*'
            )

        conn.execute(select(func.pg_advisory_unlock(SCHEDULER_LOCK_NUMBER)))

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


def test_v2_scheduler_job_lifecycle_with_heatmap(api_agent, queue, target_factory):
    """job assign route test"""

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 1
    target_factory.create(queue=queue, target='127.0.0.1', hashval=SchedulerService.hashval('127.0.0.1'))
    target_factory.create(queue=queue, target='127.0.0.2', hashval=SchedulerService.hashval('127.0.0.2'))

    assert len(Target.query.all()) == 2
    assert len(Readynet.query.all()) == 1
    assert len(Job.query.all()) == 0
    assert len(Heatmap.query.all()) == 0

    response = api_agent.post_json(url_for('api.v2_scheduler_job_assign_route'))
    assert response.status_code == HTTPStatus.OK
    assignment = response.json
    assert assignment

    assert len(Target.query.all()) == 1
    assert len(Readynet.query.all()) == 0
    assert len(Job.query.all()) == 1
    assert len(Heatmap.query.all()) == 1

    response = api_agent.post_json(
        url_for('api.v2_scheduler_job_output_route'),
        {'id': assignment['id'], 'retval': 12345, 'output': base64.b64encode(b'a-test-file-contents').decode('utf-8')},
    )
    assert response.status_code == HTTPStatus.OK

    assert len(Target.query.all()) == 1
    assert len(Readynet.query.all()) == 1
    assert len(Job.query.all()) == 1


def test_v2_stats_prometheus_route(client, queue):  # pylint: disable=unused-argument
    """job prometheus stats route test"""

    response = client.get(url_for('api.v2_stats_prometheus_route'))
    assert response.status_code == HTTPStatus.OK


def test_v2_public_storage_host_route_nonetworks(api_user_nonetworks, host):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_host_route'), {'address': host.address})
    assert not response.json


def test_v2_public_storage_host_route(api_user, host_factory, service_factory, service):
    """test public host api"""

    service_factory.create(host=host_factory.create(address='2001:db8::11'), proto='udp', port=0, state='open:test')
    host_factory.create(address='192.0.2.1')

    # DEPRECATED
    response = api_user.get(url_for('api.v2_public_storage_host_route_get', address=service.host.address))
    assert api_schema.PublicHostSchema().load(response.json)
    assert response.json['address'] == service.host.address
    assert len(response.json['services']) == 1

    # ipv4
    response = api_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': service.host.address})
    assert api_schema.PublicHostSchema().load(response.json)
    assert response.json['address'] == service.host.address
    assert len(response.json['services']) == 1

    # ipv6
    response = api_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': '2001:db8:0000::11'})
    assert api_schema.PublicHostSchema().load(response.json)
    assert response.json['address'] == '2001:db8::11'
    assert len(response.json['services']) == 1

    # query not-allowed ip
    response = api_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': '192.0.2.1'})
    assert not response.json


def test_v2_public_storage_host_route_morenotes(api_user, service, note_factory):
    """test public host api with host and service notes"""

    note_factory.create(host=service.host, xtype='xtest', data='host note data1')
    note_factory.create(host=service.host, service=service, xtype='xtest', data='service note data2')

    response = api_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': service.host.address})
    assert len(response.json['notes']) == 1
    assert len(response.json['services'][0]['notes']) == 1


def test_v2_public_storage_range_route_nonetworks(api_user_nonetworks, host):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_range_route'), {'cidr': f'{host.address}/32'})
    assert not response.json


def test_v2_public_storage_range_route(api_user, host_factory):
    """test public range api"""

    host_factory.create(address='127.0.1.1')
    host_factory.create(address='127.0.2.1')

    # DEPRECATED
    response = api_user.get(url_for('api.v2_public_storage_range_route_get', cidr='127.0.0.0/8'))
    assert api_schema.PublicRangeSchema(many=True).load(response.json)
    assert len(response.json) == 2

    response = api_user.post_json(url_for('api.v2_public_storage_range_route'), {'cidr': '127.0.0.0/8'})
    assert api_schema.PublicRangeSchema(many=True).load(response.json)
    assert len(response.json) == 2


def test_v2_public_storage_servicelist_route_nonetworks(api_user_nonetworks, service):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_servicelist_route'), {'filter': f'Service.port=="{service.port}"'})
    assert not response.json


def test_v2_public_storage_servicelist_route(api_user, service_factory):
    """test public servicelist api"""

    service_factory.create(port=1)
    service_factory.create(port=2)

    response = api_user.post_json(url_for('api.v2_public_storage_servicelist_route'), {'filter': 'Service.port=="1"'})
    assert api_schema.PublicServicelistSchema(many=True).load(response.json)
    assert len(response.json) == 1

    response = api_user.post_json(url_for('api.v2_public_storage_servicelist_route'), {'filter': 'invalid'}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_v2_public_storage_notelist_route_nonetworks(api_user_nonetworks, note):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_notelist_route'), {'filter': f'Note.xtype=="{note.xtype}"'})
    assert not response.json


def test_v2_public_storage_notelist_route(api_user, note_factory):
    """test public notelist api"""

    note_factory.create(data='dummy1')
    note_factory.create(data='dummy2')

    response = api_user.post_json(url_for('api.v2_public_storage_notelist_route'), {'filter': 'Note.data=="dummy1"'})
    assert api_schema.PublicNotelistSchema(many=True).load(response.json)
    assert len(response.json) == 1

    response = api_user.post_json(url_for('api.v2_public_storage_notelist_route'), {'filter': 'invalid'}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_v2_public_storage_versioninfo_route_nonetworks(api_user_nonetworks, versioninfo):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_versioninfo_route'))
    assert not response.json


def test_v2_public_storage_versioninfo_route(api_user, versioninfo):  # pylint: disable=unused-argument
    """test public versioninfo query api"""

    response = api_user.post_json(url_for('api.v2_public_storage_versioninfo_route'))
    assert api_schema.PublicVersionInfoSchema(many=True).load(response.json)
    assert len(response.json) == 6

    response = api_user.post_json(url_for('api.v2_public_storage_versioninfo_route'), {'product': 'ApAcHe', 'versionspec': '>1.0'})
    assert api_schema.PublicVersionInfoSchema(many=True).load(response.json)
    assert len(response.json) == 1
    assert response.json[0]["product"] == "apache httpd"

    response = api_user.post_json(url_for('api.v2_public_storage_versioninfo_route'), {'product': 'ApAcHe', 'versionspec': '<1.0'})
    assert len(response.json) == 0

    response = api_user.post_json(url_for('api.v2_public_storage_versioninfo_route'), {'filter': 'invalid'}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_v2_public_storage_vulnsearch_route_nonetworks(api_user_nonetworks, vulnsearch):  # pylint: disable=unused-argument
    """test queries with user without any configured networks"""

    response = api_user_nonetworks.post_json(url_for('api.v2_public_storage_vulnsearch_route'))
    assert not response.json


def test_v2_public_storage_vulnsearch_route(api_user, vulnsearch):  # pylint: disable=unused-argument
    """test public vulnsearch query api"""

    response = api_user.post_json(url_for('api.v2_public_storage_vulnsearch_route'))
    assert api_schema.PublicVulnsearchSchema(many=True).load(response.json)
    assert len(response.json) == 1

    response = api_user.post_json(url_for('api.v2_public_storage_vulnsearch_route'), {'filter': 'invalid'}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
