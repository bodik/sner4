"""agent processhandling tests"""

import multiprocessing
import os
import time

import pytest

from sner.agent import main
from sner.server.model.scheduler import Queue, Target, Task
from tests.server import persist_and_detach


@pytest.fixture
def test_longrun_target():
    """queue target fixture"""

    task = Task(name='test_task', module='nmap', params='-Pn --reason -sU --max-rate 1 --data-string MARKEDPROCESS')
    persist_and_detach(task)
    queue = Queue(name='test_queue', task=task, group_size=1, priority=10)
    persist_and_detach(queue)
    target = Target(target='127.126.125.124', queue=queue)
    yield persist_and_detach(target)


def test_agent_process_management(live_server, test_longrun_target):  # pylint: disable=redefined-outer-name
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(
        target=main,
        args=(['--server', live_server.url(), '--debug', '--queue', str(test_longrun_target.queue_id), '--oneshot'],))
    proc_agent.start()

    time.sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    proc_mngr = multiprocessing.Process(target=main, args=(['--terminate', str(proc_agent.pid)],))
    proc_mngr.start()
    proc_mngr.join()

    time.sleep(3)
    procs_list = os.popen('ps -f').read()
    assert 'MARKEDPROCESS' not in procs_list
    assert not proc_agent.is_alive()
    proc_agent.join()
