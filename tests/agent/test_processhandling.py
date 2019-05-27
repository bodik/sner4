"""agents process handling"""

import json
import multiprocessing
import os
import time

from sner.agent import main as agent_main


def test_terminate_with_assignment(tmpworkdir, cleanup_markedprocess, test_longrun_a):  # pylint: disable=unused-argument
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


def test_terminate_with_liveserver(tmpworkdir, live_server, cleanup_markedprocess, test_longrun_target):  # pylint: disable=unused-argument
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
