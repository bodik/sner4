# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
tests agent fixtures
"""

import re
import os
import signal
from uuid import uuid4

import pytest


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
def dummy_a():
    """test dummy assignment"""

    yield {
        'id': str(uuid4()),
        'module': 'dummy',
        'params': '--static_assignment',
        'targets': ['target1']
    }


@pytest.fixture
def longrun_a():
    """longrun assignment fixture"""

    yield {
        'id': str(uuid4()),
        'module': 'nmap',
        'params': '-Pn --reason -sT --max-rate 1 --data-string MARKEDPROCESS',
        'targets': ['127.0.0.127']
    }


@pytest.fixture
def dummy_target(dummy_a, task_factory, queue_factory, target_factory):  # pylint: disable=redefined-outer-name
    """dummy target fixture"""

    task = task_factory.create(name='test_task', module=dummy_a['module'], params=dummy_a['params'])
    queue = queue_factory.create(task=task, name='testqueue')
    target = target_factory.create(queue=queue, target=dummy_a['targets'][0])
    yield target


@pytest.fixture
def longrun_target(longrun_a, task_factory, queue_factory, target_factory):  # pylint: disable=redefined-outer-name
    """queue target fixture"""

    task = task_factory.create(name='test_task', module=longrun_a['module'], params=longrun_a['params'])
    queue = queue_factory.create(task=task, name='testqueue')
    target = target_factory.create(queue=queue, target=longrun_a['targets'][0])
    yield target
