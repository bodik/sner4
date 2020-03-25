# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
tests agent fixtures
"""

import re
import os
import signal
from uuid import uuid4

import pytest

from sner.server.scheduler.models import Queue, Target, Task
from tests import persist_and_detach


@pytest.fixture
def cleanup_markedprocess():
    """will cleanup markedprocess from failed testcase"""

    yield
    procs_list = os.popen('ps -f').read().splitlines()
    marked_procs = list(filter(lambda x: 'MARKEDPROCESS' in x, procs_list))
    marked_procs_pids = list(map(lambda x: int(re.split(r' +', x, maxsplit=7)[1]), marked_procs))
    for pid in marked_procs_pids:
        os.kill(pid, signal.SIGTERM)


@pytest.fixture
def test_dummy_a():
    """test dummy assignment"""

    yield {'id': str(uuid4()), 'module': 'dummy', 'params': '--static_assignment', 'targets': ['target1']}


@pytest.fixture
def test_dummy_target(test_dummy_a):  # pylint: disable=redefined-outer-name
    """dummy target fixture"""

    task = Task(name='test_task', module=test_dummy_a['module'], params=test_dummy_a['params'], group_size=1)
    persist_and_detach(task)
    queue = Queue(task=task, name='testqueue', priority=10, active=True)
    persist_and_detach(queue)
    target = Target(target=test_dummy_a['targets'][0], queue=queue)
    yield persist_and_detach(target)


@pytest.fixture
def test_longrun_a():
    """longrun assignment fixture"""

    yield {
        'id': str(uuid4()),
        'module': 'nmap',
        'params': '-Pn --reason -sT --max-rate 1 --data-string MARKEDPROCESS',
        'targets': ['127.0.0.127']}


@pytest.fixture
def test_longrun_target(test_longrun_a):  # pylint: disable=redefined-outer-name
    """queue target fixture"""

    task = Task(name='test_task', module=test_longrun_a['module'], params=test_longrun_a['params'], group_size=1)
    persist_and_detach(task)
    queue = Queue(task=task, name='testqueue', priority=10, active=True)
    persist_and_detach(queue)
    target = Target(target=test_longrun_a['targets'][0], queue=queue)
    yield persist_and_detach(target)
