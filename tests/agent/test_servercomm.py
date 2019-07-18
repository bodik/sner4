# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
tests with various server communication test cases
"""

import multiprocessing
import signal
from contextlib import contextmanager
from http import HTTPStatus
from time import sleep
from uuid import uuid4

import pytest
import requests
from flask import _request_ctx_stack, current_app, Flask, jsonify
from pytest_flask.fixtures import live_server

from sner.agent import main as agent_main, TerminateException


@contextmanager
def terminate_after(time):
    """
    timed termination helper; will raise internal agent's exception.
    Raised exception is designed not to be catched by module runner loop and should end agent properly from within.
    """

    def raise_terminate(signum, frame):  # pylint: disable=unused-argument
        raise TerminateException

    signal.signal(signal.SIGALRM, raise_terminate)
    signal.alarm(time)
    try:
        yield
    except TerminateException:
        pass
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


@pytest.fixture('function')
def fail_server(request, monkeypatch, pytestconfig):
    """errors injection server used to test edge-cases in agent's codebase"""

    class Xflask(Flask):
        """error injecting flask app"""
        def __init__(self, import_name):
            super().__init__(import_name)
            self.nr_assign = 0
            self.nr_output = 0
            self.assign_done = False
            self.output_done = False
    app = Xflask('fail_server')

    @app.route('/api/v1/scheduler/job/assign')
    def assign_route():  # pylint: disable=unused-variable
        if _request_ctx_stack.top.request.headers.get('Authorization') != 'Apikey dummy-breaks-duplicate-code1':
            return 'Unauthorized', HTTPStatus.UNAUTHORIZED

        if current_app.nr_assign < 2:
            current_app.nr_assign += 1
            return jsonify({'response': 'invalid'})

        current_app.assign_done = True
        return jsonify({'id': uuid4(), 'module': 'dummy', 'params': '', 'targets': []})

    @app.route('/api/v1/scheduler/job/output', methods=['POST'])
    def output_route():  # pylint: disable=unused-variable
        if _request_ctx_stack.top.request.headers.get('Authorization') != 'Apikey dummy-breaks-duplicate-code1':
            return 'Unauthorized', HTTPStatus.UNAUTHORIZED

        if current_app.nr_output < 1:
            current_app.nr_output += 1
            return jsonify({'title': 'output upload failed'}), HTTPStatus.BAD_REQUEST

        current_app.output_done = True
        return '', HTTPStatus.OK

    @app.route('/check')
    def check():  # pylint: disable=unused-variable
        return jsonify({'assign_done': current_app.assign_done, 'output_done': current_app.output_done})

    yield live_server(request, app, monkeypatch, pytestconfig)


# using direct call to supply custom app for live_server
@pytest.mark.filterwarnings('ignore:Fixture "live_server" called directly:DeprecationWarning')
def test_fail_server_communication(tmpworkdir, fail_server):  # pylint: disable=unused-argument,redefined-outer-name
    """tests failure handling while retrieving assignment or uploading output"""

    # oneshot will abort upon first get_assignment error, coverage for external
    # processes is not working yet. to test the agent's communication error
    # handling: the agent will run in-thread, will be breaked by
    # signal/exception and fail_server internals will be checked manualy

    with terminate_after(1):
        agent_main(['--server', fail_server.url(), '--apikey', 'dummy-breaks-duplicate-code1', '--debug', '--backofftime', '0.1'])

    response = requests.get('%s/check' % fail_server.url()).json()
    assert response['assign_done']
    assert response['output_done']


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
    proc_agent.join(3)
    assert not proc_agent.is_alive()


def test_invalid_server_oneshot(tmpworkdir):  # pylint: disable=unused-argument,redefined-outer-name
    """test to raise exception in oneshot"""

    result = agent_main(['--server', 'http://localhost:0', '--debug', '--oneshot'])
    assert result == 1
