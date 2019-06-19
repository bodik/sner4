"""agents process handling"""

import json
import multiprocessing
import os
from http import HTTPStatus
from time import sleep
from uuid import uuid4

import pytest
from flask import Flask, jsonify
from pytest_flask.fixtures import live_server

from sner.agent import main as agent_main


def test_terminate_with_assignment(tmpworkdir, cleanup_markedprocess, test_longrun_a):  # pylint: disable=unused-argument
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--assignment', json.dumps(test_longrun_a), '--debug'],))
    proc_agent.start()
    sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    agent_main(['--terminate', str(proc_agent.pid)])
    proc_agent.join(3)
    assert not proc_agent.is_alive()
    assert 'MARKEDPROCESS' not in os.popen('ps -f').read()


def test_terminate_with_liveserver(tmpworkdir, live_server, cleanup_markedprocess, test_longrun_target):  # noqa: ignore=E501  pylint: disable=unused-argument,redefined-outer-name
    """agent's external process handling test"""

    proc_agent = multiprocessing.Process(
        target=agent_main,
        args=(['--server', live_server.url(), '--debug', '--queue', str(test_longrun_target.queue_id), '--oneshot'],))
    proc_agent.start()
    sleep(1)
    assert proc_agent.pid
    assert proc_agent.is_alive()

    agent_main(['--terminate', str(proc_agent.pid)])
    proc_agent.join(3)
    assert not proc_agent.is_alive()
    assert 'MARKEDPROCESS' not in os.popen('ps -f').read()


@pytest.fixture
def simple_server(request, monkeypatch, pytestconfig):
    """simple server for testing normal communication"""

    app = Flask('simple_server')

    @app.route('/api/v1/scheduler/job/assign')
    def assign_route():  # pylint: disable=unused-variable
        return jsonify({'id': uuid4(), 'module': 'dummy', 'params': '', 'targets': []})

    @app.route('/api/v1/scheduler/job/output', methods=['POST'])
    def output_route():  # pylint: disable=unused-variable
        return jsonify({'status': HTTPStatus.OK}), HTTPStatus.OK

    yield live_server(request, app, monkeypatch, pytestconfig)


# using direct call to supply custom app for live_server
@pytest.mark.filterwarnings('ignore:Fixture "live_server" called directly:DeprecationWarning')
def test_shutdown(tmpworkdir, simple_server):  # pylint: disable=unused-argument,redefined-outer-name
    """test no-work, continuous job assignment and shutdown signal handling"""

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--server', simple_server.url(), '--debug'],))
    proc_agent.start()
    sleep(1)
    assert proc_agent.is_alive()

    agent_main(['--shutdown', str(proc_agent.pid)])
    proc_agent.join(1)
    assert not proc_agent.is_alive()
