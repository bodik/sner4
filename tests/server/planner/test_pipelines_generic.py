# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner standalone pipelines tests
"""

import logging
import os
from ipaddress import ip_address

import pytest
from flask import current_app

from sner.server.extensions import db
from sner.server.planner.commands import command
from sner.server.planner.core import Planner
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Service
from sner.server.utils import yaml_dump


def test_pipeline_debug_step(runner, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test dummy debug step pipeline"""

    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [{'step': 'debug'}]
        }
    ]

    Planner(oneshot=True).run()

    assert True


def test_pipeline_rescan_services(runner, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline"""

    service_factory.create(host=host_factory.create(address='127.0.0.1'))
    service_factory.create(host=host_factory.create(address='::1'))
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'rescan_services',
                    'interval': '0s',
                    'queue': 'test vscan',
                }
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert Target.query.count() == 2


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='large dataset test is slow')
def test_pipeline_rescan_services_largedataset(runner, queue_factory, host_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline testing with large dataset"""

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
        host = host_factory.create(address=str(ip_address(addr)))
        # bypass all db layers for performance
        query = 'INSERT INTO service (host_id, proto, port, tags) VALUES ' + ','.join([str((host.id, 'tcp', str(idx), '{}')) for idx in range(64000)])
        db.session.execute(query)
        logging.info('prepared %s', host)
    logger.info('lot_of_services prepare end')

    db.session.expire_all()

    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'rescan_services',
                    'interval': '0s',
                    'queue': 'test vscan',
                }
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert Target.query.count() == existing_targets_count + Service.query.count()


def test_pipeline_rescan_hosts(runner, host_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_hosts pipeline"""

    host_factory.create(address='127.0.0.1')
    host_factory.create(address='::1')
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'rescan_hosts',
                    'interval': '0s',
                    'queue': 'test vscan',
                }
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert Target.query.count() == 2


def test_pipeline_discover_ipv4(runner, queue):  # pylint: disable=unused-argument
    """test discover ipv4 pipeline"""

    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'discover_ipv4',
                    'interval': '1h',
                    'netranges': ['127.0.0.0/24'],
                    'queue': queue.name
                }
            ]
        }
    ]

    Planner(oneshot=True).run()
    # trigger backoff timer block coverage
    Planner(oneshot=True).run()

    assert Target.query.count() == 256


def test_pipeline_discover_ipv6_dns_stage(runner, queue):  # pylint: disable=unused-argument
    """test discover ipv6 dns pipeline"""

    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'discover_ipv6_dns',
                    'interval': '1h',
                    'netranges': ['127.0.0.0/24'],
                    'queue': queue.name
                }
            ]
        }
    ]

    Planner(oneshot=True).run()
    # trigger backoff timer block coverage
    Planner(oneshot=True).run()

    assert Target.query.count() == 256


def test_pipeline_discover_ipv6_enum_stage(runner, queue, host_factory):  # pylint: disable=unused-argument
    """test discover ipv6 enum pipeline"""

    host_factory.create(address='::1')
    host_factory.create(address='::00ff:fe00:1')
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [
                {
                    'step': 'discover_ipv6_enum',
                    'interval': '1h',
                    'queue': queue.name
                }
            ]
        }
    ]

    Planner(oneshot=True).run()
    # trigger backoff timer block coverage
    Planner(oneshot=True).run()

    assert Target.query.count() == 1


def test_pipeline_storage_cleanup(runner, host_factory, service_factory, note_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    host1 = host_factory.create(address='127.127.127.135', os='identified')
    service_factory.create(host=host1, proto='tcp', port=1, state='open:reason')
    service_factory.create(host=host1, proto='tcp', port=1, state='filtered:reason')
    host2 = host_factory.create(address='127.127.127.136', hostname=None, os=None, comment=None)
    note_factory.create(host=host2, xtype='hostnames', data='adata')
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'generic',
            'steps': [{'step': 'storage_cleanup'}]
        }
    ]

    runner.invoke(command, ['run', '--oneshot'])

    assert Host.query.count() == 1
    assert Service.query.count() == 1
