# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner most used pipelines tests
"""

import logging
import os
from ipaddress import ip_address
from pathlib import Path

import pytest
import yaml
from flask import current_app

from sner.server.extensions import db
from sner.server.planner.core import Planner
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Service
from sner.server.utils import yaml_dump


def test_discovery_pipeline(runner, queue_factory):  # pylint: disable=unused-argument
    """test discovery pipeline"""

    queue_factory.create(name='queue1', config=yaml_dump({'module': 'nmap', 'args': 'arg1'}))
    queue_factory.create(name='queue2', config=yaml_dump({'module': 'nmap', 'args': 'arg2'}))

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
        common:
          home_netranges_ipv4: &home_netranges_ipv4 ['127.0.0.0/24']

        step_groups:
          service_discovery:
            - step: enqueue
              queue: 'queue1'
            - step: enqueue
              queue: 'queue2'

        pipelines:
          - type: interval
            name: discover_ipv4
            interval: 120days
            steps:
              - step: enumerate_ipv4
                netranges: *home_netranges_ipv4
              - step: run_group
                name: service_discovery
    """)

    Planner(oneshot=True).run()

    assert Target.query.count() == 2*256


def test_scanning_pipeline(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test scanning pipeline"""

    queue1 = queue_factory.create(name='queue1', config=yaml_dump({'module': 'nmap', 'args': 'arg1'}))
    job_completed_factory.create(
        queue=queue1,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )
    queue_factory.create(name='queue2', config=yaml_dump({'module': 'nmap', 'args': 'arg2'}))
    queue_factory.create(name='queue3', config=yaml_dump({'module': 'nmap', 'args': 'arg3'}))

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
        step_groups:
          service_scanning:
            - step: enqueue
              queue: 'queue2'
            - step: enqueue
              queue: 'queue3'

        pipelines:
          - type: queue
            steps:
              - step: load_job
                queue: 'queue1'
              - step: filter_tarpits
              - step: project_servicelist
              - step: run_group
                name: service_scanning
              - step: archive_job
    """)

    Planner(oneshot=True).run()

    assert Target.query.count() == 10


def test_import_pipeline(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test import pipeline"""

    queue = queue_factory.create(name='queue1', config=yaml_dump({'module': 'nmap', 'args': 'arg1'}))
    job_completed_factory.create(queue=queue, make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes())

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
        pipelines:
          - type: queue
            steps:
              - step: load_job
                queue: 'queue1'
              - step: import_job
              - step: archive_job
    """)

    Planner(oneshot=True).run()

    assert len(Host.query.all()) == 1
    assert len(Service.query.all()) == 5


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='large dataset test is slow')
def test_pipeline_rescan_services_largedataset(runner, queue_factory, host_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline testing with large dataset"""

    logger = logging.getLogger(__name__)

    logger.info('lot_of_targets prepare start')
    queue = queue_factory.create(name='queue1', config=yaml_dump({'module': 'nmap', 'args': 'arg1'}))
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

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
        pipelines:
          - type: generic
            steps:
              - step: rescan_services
                interval: '0s'
              - step: enqueue
                queue: queue1
    """)

    Planner(oneshot=True).run()

    assert Target.query.count() == existing_targets_count + Service.query.count()
