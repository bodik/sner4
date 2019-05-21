"""scheduler test models"""

import datetime
import json
import uuid

import pytest

from sner.server.model.scheduler import Job, Queue, Target, Task
from tests.server import persist_and_detach


def create_test_task():
    """test task data"""

    return Task(
        name='test task name',
        module='test',
        params='--arg1 abc --arg2')


def create_test_queue(a_test_task):
    """test queue data"""

    return Queue(
        name='queue name',
        task=a_test_task,
        group_size=2,
        priority=10,
        active=False)


def create_test_target(a_test_queue):
    """test target data"""

    return Target(
        target='testtarget',
        queue=a_test_queue)


def create_test_job(a_test_queue):
    """test job data"""

    return Job(
        id=str(uuid.uuid4()),
        queue=a_test_queue,
        assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
        time_start=datetime.datetime.now(),
        time_end=datetime.datetime.now())


@pytest.fixture
def test_task():
    """persistent test task"""

    yield persist_and_detach(create_test_task())


@pytest.fixture
def test_queue(test_task): # pylint: disable=redefined-outer-name
    """persistent test queue"""

    yield persist_and_detach(create_test_queue(test_task))


@pytest.fixture
def test_target(test_queue): # pylint: disable=redefined-outer-name
    """persistent test queue"""

    yield persist_and_detach(create_test_target(test_queue))


@pytest.fixture
def test_job(test_queue): # pylint: disable=redefined-outer-name
    """persistent test job"""

    yield persist_and_detach(create_test_job(test_queue))
