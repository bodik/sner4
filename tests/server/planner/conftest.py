# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner fixtures
"""

from pathlib import Path

import pytest

from sner.server.parser import ParsedItemsDb
from sner.server.utils import yaml_dump


@pytest.fixture
def job_completed_nmap(queue_factory, job_completed_factory):
    """mock completed nmap job with real data"""

    queue = queue_factory.create(
        name='test queue',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    yield job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )


@pytest.fixture
def job_completed_sixenumdiscover(queue_factory, job_completed_factory):
    """mock completed nmap job with real data"""

    queue = queue_factory.create(
        name='test queue',
        config=yaml_dump({'module': 'six_enum_discover', 'args': 'arg1'}),
    )
    yield job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-six_enum_discover-job.zip').read_bytes()
    )


@pytest.fixture
def sample_pidb():
    """mock sample pidb"""

    pidb = ParsedItemsDb()

    host = pidb.upsert_host('127.0.3.1')
    pidb.upsert_service(host.address, 'tcp', 1)

    host = pidb.upsert_host('127.0.4.1')
    for port in range(201):
        pidb.upsert_service(host.address, 'tcp', port)

    return pidb
