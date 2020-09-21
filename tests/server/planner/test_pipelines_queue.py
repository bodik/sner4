# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
test planner queue pipelines
"""

from pathlib import Path

from flask import current_app

from sner.server.planner.core import Planner
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Service
from sner.server.utils import yaml_dump


def test_pipeline_import_job(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test import typed pipeline"""

    queue = queue_factory.create(
        name='test queue disco',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'queue',
            'steps': [
                {'step': 'load_job', 'queue': queue.name},
                {'step': 'import_job'},
                {'step': 'archive_job'}
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert len(Host.query.all()) == 1
    assert len(Service.query.all()) == 5


def test_pipeline_servicelist_enqueue(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test servicelist enqueue"""

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
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'queue',
            'steps': [
                {'step': 'load_job', 'queue': queue.name},
                {'step': 'project_servicelist'},
                {'step': 'enqueue', 'queue': next_queue.name},
                {'step': 'archive_job'}
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert Target.query.count() == 5


def test_pipeline_hostlist_enqueue(runner, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test hostlist enqueue"""

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
    current_app.config['SNER_PLANNER']['pipelines'] = [
        {
            'type': 'queue',
            'steps': [
                {'step': 'load_job', 'queue': queue.name},
                {'step': 'project_hostlist'},
                {'step': 'filter_netranges', 'netranges': ['::1/128']},
                {'step': 'enqueue', 'queue': next_queue.name},
                {'step': 'archive_job'}
            ]
        }
    ]

    Planner(oneshot=True).run()

    assert Target.query.count() == 1
