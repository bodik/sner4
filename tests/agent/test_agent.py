"""agent processhandling tests"""

import json
import multiprocessing
import os
import time
from uuid import uuid4
from zipfile import ZipFile

from sner.agent import main as agent_main
from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job


def test_commandline_assignment(tmpworkdir, test_dummy_a):
    """test custom assignment passed from command line"""

    result = agent_main(['--assignment', json.dumps(test_dummy_a)])
    assert result == 0
    assert os.path.exists(test_dummy_a['id'])


def test_exception_in_module(tmpworkdir):
    """test exception handling during agent module execution"""

    test_a = {'id': str(uuid4()), 'module': 'notexist', 'params': '', 'targets': []}

    result = agent_main(['--assignment', json.dumps(test_a)])
    assert result == 1
    assert os.path.exists(test_a['id'])


def test_run_with_liveserver(tmpworkdir, live_server, test_dummy_target):
    """test basic agent's networking codepath; fetch, execute, pack and upload assignment"""

    result = agent_main(['--server', live_server.url(), '--debug', '--queue', str(test_dummy_target.queue_id), '--oneshot'])
    assert result == 0

    job = Job.query.filter(Job.queue_id == test_dummy_target.queue_id).one_or_none()
    assert job
    with ZipFile(job_output_filename(job.id)) as ftmp_zip:
        with ftmp_zip.open('assignment.json') as ftmp:
            assert test_dummy_target.target in ftmp.read().decode('utf-8')


def test_terminate_with_assignment(tmpworkdir, cleanup_markedprocess, test_longrun_a):
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--assignment', json.dumps(test_longrun_a), '--debug'],))
    proc_agent.start()
    time.sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    agent_main(['--terminate', str(proc_agent.pid)])
    time.sleep(3)
    assert 'MARKEDPROCESS' not in os.popen('ps -f').read()
    assert not proc_agent.is_alive()
    proc_agent.join()


def test_terminate_with_liveserver(tmpworkdir, live_server, cleanup_markedprocess, test_longrun_target):
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
    assert 'MARKEDPROCESS' not in os.popen('ps -f').read()
    assert not proc_agent.is_alive()
    proc_agent.join()
