"""agent processhandling tests"""

import json
import multiprocessing
import os
import re
import shutil
import signal
import time
from uuid import uuid4
from zipfile import ZipFile

import pytest

from sner.agent import main as agent_main
from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job, Queue, Target, Task
from tests import persist_and_detach


@pytest.fixture
def test_assignment():
    """generate static assignment and cleanup on test fail"""

    assignment = {'id': str(uuid4()), 'module': 'dummy', 'params': '--static_assignment', 'targets': ['target1']}
    yield assignment
    if os.path.exists(assignment['id']):
        shutil.rmtree(assignment['id'])


@pytest.fixture
def test_assignment_exception():
    """invalid assignment to test agent module call exception handling"""

    assignment = {'id': str(uuid4()), 'module': 'notexist', 'params': '', 'targets': []}
    yield assignment
    if os.path.exists(assignment['id']):
        shutil.rmtree(assignment['id'])


@pytest.fixture
def test_dummy_target():
    """dummy target fixture"""

    task = Task(name='test_task', module='dummy', params='--someargument argvalue')
    persist_and_detach(task)
    queue = Queue(name='test_queue', task=task, group_size=1, priority=10)
    persist_and_detach(queue)
    target = Target(target='testtarget', queue=queue)
    yield persist_and_detach(target)


@pytest.fixture
def test_longrun_assignment():
    assignment = {'id': str(uuid4()), 'module': 'nmap', 'params': '-Pn --reason -sU --max-rate 1 --data-string MARKEDPROCESS', 'targets': ['127.0.0.127']}
    yield assignment
    if os.path.exists(assignment['id']):
        shutil.rmtree(assignment['id'])


@pytest.fixture
def test_longrun_target():
    """queue target fixture"""

    task = Task(name='test_task', module='nmap', params='-Pn --reason -sU --max-rate 1 --data-string MARKEDPROCESS')
    persist_and_detach(task)
    queue = Queue(name='test_queue', task=task, group_size=1, priority=10)
    persist_and_detach(queue)
    target = Target(target='127.0.0.127', queue=queue)
    yield persist_and_detach(target)


@pytest.fixture
def cleanup_markedprocess():
    """will cleanup markedprocess from failed testcase"""

    yield
    procs_list = os.popen('ps -f').read().splitlines()
    marked_procs = list(filter(lambda x: 'MARKEDPROCESS' in x, procs_list))
    marked_procs_pids = list(map(lambda x: int(re.split(r' +', x, maxsplit=7)[1]), marked_procs))
    for pid in marked_procs_pids:
        os.kill(pid, signal.SIGTERM)


def test_commandline_assignment(test_assignment):  # pylint: disable=redefined-outer-name
    """test custom assignment passed from command line"""

    result = agent_main(['--assignment', json.dumps(test_assignment)])
    assert result == 0
    assert os.path.exists(test_assignment['id'])
    assert os.path.exists('%s/assignment.json' % test_assignment['id'])


def test_exception_in_module(test_assignment_exception):  # pylint: disable=redefined-outer-name
    """test exception handling during agent module execution"""

    result = agent_main(['--assignment', json.dumps(test_assignment_exception)])
    assert result == 1
    assert os.path.exists(test_assignment_exception['id'])


def test_run_with_liveserver(live_server, test_dummy_target):  # pylint: disable=redefined-outer-name
    """test basic agent's networking codepath; fetch, execute, pack and upload assignment"""

    result = agent_main(['--server', live_server.url(), '--debug', '--queue', str(test_dummy_target.queue_id), '--oneshot'])
    assert result == 0

    job = Job.query.filter(Job.queue_id == test_dummy_target.queue_id).one_or_none()
    assert job
    with ZipFile(job_output_filename(job.id)) as ftmp_zip:
        with ftmp_zip.open('assignment.json') as ftmp:
            assert test_dummy_target.target in ftmp.read().decode('utf-8')


def test_terminate_with_assignment(test_longrun_assignment, cleanup_markedprocess):  # pylint: disable=redefined-outer-name
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--assignment', json.dumps(test_longrun_assignment), '--debug',],))
    proc_agent.start()

    time.sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    agent_main(['--terminate', str(proc_agent.pid)])

    time.sleep(3)
    procs_list = os.popen('ps -f').read()
    assert 'MARKEDPROCESS' not in procs_list
    assert not proc_agent.is_alive()
    proc_agent.join()


def test_terminate_with_liveserver(live_server, test_longrun_target, cleanup_markedprocess):  # pylint: disable=redefined-outer-name
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(
        target=agent_main,
        args=(['--server', live_server.url(), '--debug', '--queue', str(test_longrun_target.queue_id), '--oneshot'],))
    proc_agent.start()

    time.sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    agent_main(['--terminate', str(proc_agent.pid)])

    time.sleep(3)
    procs_list = os.popen('ps -f').read()
    assert 'MARKEDPROCESS' not in procs_list
    assert not proc_agent.is_alive()
    proc_agent.join()
