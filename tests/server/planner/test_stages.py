# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner stages tests
"""

import logging
import os
from ipaddress import IPv4Address
from pathlib import Path

import pytest
from flask import current_app

import sner.server.planner.stages
from sner.server.extensions import db
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Service
from sner.server.utils import yaml_dump


def test_import_stage(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test import stage"""

    queue = queue_factory.create(
        name='test queue version scan',
        config=yaml_dump({'module': 'manymap', 'args': 'arg1'}),
    )
    job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-manymap-job.zip').read_bytes()
    )
    current_app.config['SNER_PLANNER'] = {'import_jobs': [queue.name]}

    sner.server.planner.stages.import_jobs()

    assert Host.query.count() == 1
    assert Service.query.count() == 1


def test_import_stage_cleanup_storage(runner, host_factory, service_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host1 = host_factory.create(address='127.127.127.135', os='identified')
    service_factory.create(host=host1, proto='tcp', port=1, state='open:reason')
    service_factory.create(host=host1, proto='tcp', port=1, state='filtered:reason')
    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)

    sner.server.planner.stages.cleanup_storage()

    hosts = Host.query.all()
    assert len(hosts) == 1
    services = Service.query.all()
    assert len(services) == 1


def test_enqueue_servicelist_stage(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test enqueue_servicelist stage"""

    next_queue = queue_factory.create(
        name='test queue version scan',
        config=yaml_dump({'module': 'manymap', 'args': 'arg1'}),
    )
    queue = queue_factory.create(
        name='test queue disco',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )
    current_app.config['SNER_PLANNER'] = {'enqueue_servicelist': [(queue.name, next_queue.name)]}

    sner.server.planner.stages.enqueue_servicelist()

    assert Target.query.count() == 5


def test_enqueue_hostlist_stage(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test enqueue_servicelist stage"""

    next_queue = queue_factory.create(
        name='test queue ack scan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    queue = queue_factory.create(
        name='test queue ipv6 dns discover',
        config=yaml_dump({'module': 'six_dns_discover', 'delay': '1'}),
    )
    job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-six_dns_discover-job.zip').read_bytes()
    )
    current_app.config['SNER_PLANNER'] = {'enqueue_hostlist': [(queue.name, next_queue.name)]}

    sner.server.planner.stages.enqueue_hostlist()

    assert Target.query.count() == 1


def test_rescan_services_stage(runner, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services stage"""

    service_factory.create(host=host_factory.create(address='127.0.0.1'))
    service_factory.create(host=host_factory.create(address='::1'))
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    current_app.config['SNER_PLANNER'] = {
        'rescan_services': {
            'interval': '0s',
            'queue4': 'test vscan',
            'queue6': 'test vscan',
        }
    }

    sner.server.planner.stages.rescan_services()

    assert Target.query.count() == 2


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='large dataset test is slow')
def test_rescan_services_stage_largedataset(runner, queue_factory, host_factory):  # pylint: disable=unused-argument
    """test rescan_services stage testing with large dataset"""

    logger = logging.getLogger(__name__)

    logger.info('lot_of_targets prepare start')
    queue = queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    existing_targets_count = 10**6
    # bypass all db layers for performance
    query = 'INSERT INTO target (queue_id, target) VALUES ' + ','.join([str((queue.id, str(idx))) for idx in range(existing_targets_count)])
    db.session.execute(query)
    logger.info('lot_of_targets prepare end')

    logger.info('lot_of_services prepare start')
    for addr in range(10):
        host = host_factory.create(address=str(IPv4Address(addr)))
        # bypass all db layers for performance
        query = 'INSERT INTO service (host_id, proto, port, tags) VALUES ' + ','.join([str((host.id, 'tcp', str(idx), '{}')) for idx in range(64000)])
        db.session.execute(query)
        logging.info('prepared %s', host)
    logger.info('lot_of_services prepare end')

    db.session.expire_all()

    current_app.config['SNER_PLANNER'] = {
        'rescan_services': {
            'interval': '0s',
            'queue4': 'test vscan',
            'queue6': 'test vscan',
        }
    }

    sner.server.planner.stages.rescan_services()

    assert Target.query.count() == existing_targets_count + Service.query.count()


def test_rescan_hosts_stage(runner, host_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services stage"""

    host_factory.create(address='127.0.0.1')
    host_factory.create(address='::1')
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    current_app.config['SNER_PLANNER'] = {
        'rescan_hosts': {
            'interval': '0s',
            'queue4': 'test vscan',
            'queue6': 'test vscan',
        }
    }

    sner.server.planner.stages.rescan_hosts()

    assert Target.query.count() == 2


def test_discover_ipv4_stage(runner, queue):  # pylint: disable=unused-argument
    """test discover ipv4"""

    current_app.config['SNER_PLANNER'] = {
        'discover_ipv4': {
            'interval': '1h',
            'netranges': ['127.0.0.0/24'],
            'queue': queue.name
        }
    }

    sner.server.planner.stages.discover_ipv4()
    sner.server.planner.stages.discover_ipv4()  # trigger backoff time coverage

    assert Target.query.count() == 256


def test_discover_ipv6_dns_stage(runner, queue):  # pylint: disable=unused-argument
    """test discover ipv6 dns"""

    current_app.config['SNER_PLANNER'] = {
        'discover_ipv6_dns': {
            'interval': '1h',
            'netranges': ['127.0.0.0/24'],
            'queue': queue.name
        }
    }

    sner.server.planner.stages.discover_ipv6_dns()
    sner.server.planner.stages.discover_ipv6_dns()

    assert Target.query.count() == 256
