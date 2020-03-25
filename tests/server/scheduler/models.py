# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler test models
"""

import json
import os
from datetime import datetime
from uuid import uuid4
from zipfile import ZipFile

import pytest

from sner.server.scheduler.models import Excl, ExclFamily, Job, Queue, Target, Task
from tests import persist_and_detach


def create_test_task():
    """test task data"""

    return Task(
        name='testtaskname',
        module='test',
        params='--arg1 abc --arg2',
        group_size=1)


def create_test_queue(a_test_task):
    """test queue data"""

    return Queue(
        name='testqueue',
        task_id=a_test_task.id,
        task=a_test_task,
        priority=10,
        active=True)


def create_test_target(a_test_queue):
    """test target data"""

    return Target(
        target='testtarget',
        queue_id=a_test_queue.id,
        queue=a_test_queue)


def create_test_job(a_test_queue):
    """test job data; only assigned"""

    return Job(
        id=str(uuid4()),
        queue_id=a_test_queue.id,
        queue=a_test_queue,
        assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
        time_start=datetime.now())


def create_test_excl_network():
    """test network exclusion data"""

    return Excl(
        family=ExclFamily.network,
        value='127.66.66.0/26',
        comment='blocked test netrange, no traffic should go there')


def create_test_excl_regex():
    """test regex exclusion data"""

    return Excl(
        family=ExclFamily.regex,
        value='notarget[012]',
        comment='targets blocked by regex')


@pytest.fixture
def test_task():
    """persistent test task"""

    yield persist_and_detach(create_test_task())


@pytest.fixture
def test_queue(test_task):  # pylint: disable=redefined-outer-name
    """persistent test queue"""

    yield persist_and_detach(create_test_queue(test_task))


@pytest.fixture
def test_target(test_queue):  # pylint: disable=redefined-outer-name
    """persistent test queue"""

    yield persist_and_detach(create_test_target(test_queue))


@pytest.fixture
def test_job(test_queue):  # pylint: disable=redefined-outer-name
    """persistent test job assigned"""

    yield persist_and_detach(create_test_job(test_queue))


@pytest.fixture
def test_job_completed(test_queue):  # pylint: disable=redefined-outer-name
    """persistent test job completed"""

    job = create_test_job(test_queue)
    job.retval = 0
    job.output = os.path.join('scheduler', 'queue-%s' % job.queue_id, job.id)
    os.makedirs(os.path.dirname(job.output_abspath), exist_ok=True)
    with open(job.output_abspath, 'wb') as job_file:
        with ZipFile(job_file, 'w') as zip_file:
            zip_file.writestr(json.dumps(job.assignment), 'assignment.json')
    job.time_end = datetime.utcnow()
    yield persist_and_detach(job)


@pytest.fixture
def test_excl_network():
    """persistent test network exclusion"""

    yield persist_and_detach(create_test_excl_network())


@pytest.fixture
def test_excl_regex():
    """persistent test regex exclusion"""

    yield persist_and_detach(create_test_excl_regex())
