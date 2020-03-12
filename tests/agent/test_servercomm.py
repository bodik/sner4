# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
tests with various server communication test cases
"""

import json
import multiprocessing
import os
import signal
from contextlib import contextmanager
from http import HTTPStatus
from time import sleep
from uuid import uuid4

from werkzeug.wrappers import Response

from sner.agent import main as agent_main


@contextmanager
def terminate_after(time):
    """
    timed termination helper; will raise internal agent's exception.
    Raised exception is designed not to be catched by module runner loop and should end agent properly from within.
    """

    def signal_terminate(signum, frame):  # pylint: disable=unused-argument
        os.kill(os.getpid(), signal.SIGTERM)

    signal.signal(signal.SIGALRM, signal_terminate)
    signal.alarm(time)
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


class FailServer():
    """error injecting server used to test edge-cases in agent's codebase"""

    def __init__(self, server):
        self.server = server
        self.url = self.server.url_for('/')[:-1]
        self.cnt_assign = 0
        self.cnt_output = 0
        self.server.expect_request('/api/v1/scheduler/job/assign').respond_with_handler(self.handler_assign)
        self.server.expect_request('/api/v1/scheduler/job/output').respond_with_handler(self.handler_output)

    def handler_assign(self, request):
        """handle assign request"""
        if request.headers.get('Authorization') != 'Apikey dummy':
            return Response('Unauthorized', status=HTTPStatus.UNAUTHORIZED)
        if self.cnt_assign < 2:
            self.cnt_assign += 1
            return Response(json.dumps({'response': 'invalid'}))
        return Response(json.dumps({'id': str(uuid4()), 'module': 'dummy', 'params': '', 'targets': []}))

    def handler_output(self, request):
        """handle output request"""
        if request.headers.get('Authorization') != 'Apikey dummy':
            return Response('Unauthorized', status=HTTPStatus.UNAUTHORIZED)
        if self.cnt_output < 2:
            self.cnt_output += 1
            return Response(json.dumps({'title': 'output upload failed'}), status=HTTPStatus.UNAUTHORIZED)
        return Response('', status=HTTPStatus.OK)


def test_fail_server_communication(tmpworkdir, httpserver):  # pylint: disable=unused-argument,redefined-outer-name
    """tests failure handling while retrieving assignment or uploading output"""

    # oneshot will abort upon first get_assignment error, coverage for external
    # processes is not working yet. to test the agent's communication error
    # handling: the agent will run in-thread, will be breaked by
    # signal/exception and fail_server internals will be checked manualy

    sserver = FailServer(httpserver)

    with terminate_after(1):
        agent_main(['--server', sserver.url, '--apikey', 'dummy', '--debug', '--backofftime', '0.1'])

    assert sserver.cnt_assign > 1
    assert sserver.cnt_output > 1


def test_empty_server_communication(tmpworkdir, live_server, apikey):  # pylint: disable=unused-argument,redefined-outer-name
    """tests oneshot vs wait on assignment on empty server"""

    result = agent_main(['--server', live_server.url(), '--apikey', apikey, '--debug', '--oneshot'])
    assert result == 0

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--server', live_server.url(), '--apikey', apikey, '--debug'],))
    proc_agent.start()
    sleep(2)
    assert proc_agent.pid
    assert proc_agent.is_alive()
    agent_main(['--terminate', str(proc_agent.pid)])
    proc_agent.join(4)
    assert not proc_agent.is_alive()


def test_invalid_server_oneshot(tmpworkdir):  # pylint: disable=unused-argument,redefined-outer-name
    """test to raise exception in oneshot"""

    result = agent_main(['--server', 'http://localhost:0', '--debug', '--oneshot'])
    assert result == 1
