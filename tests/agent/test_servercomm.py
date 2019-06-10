"""tests with various server communication test cases"""

import multiprocessing
from http import HTTPStatus
from time import sleep
from uuid import uuid4

import pytest
from flask import current_app, Flask, jsonify
from pytest_flask.fixtures import live_server

from sner.agent import main as agent_main


@pytest.fixture
def fail_server(request, monkeypatch, pytestconfig):
    """errors injection server used to test edge-cases in agent's codebase"""

    class Xflask(Flask):
        """error injecting flask app"""
        def __init__(self, import_name):
            super().__init__(import_name)
            self.nr_assign = 0
            self.nr_output = 0
    app = Xflask('fail_server')

    @app.route('/scheduler/job/assign')
    def assign_route():  # pylint: disable=unused-variable
        if current_app.nr_assign < 1:
            current_app.nr_assign += 1
            return jsonify({'response': 'invalid'})

        if current_app.nr_assign < 2:
            current_app.nr_assign += 1
            return jsonify({'response': 'invalid'})

        return jsonify({'id': uuid4(), 'module': 'dummy', 'params': '', 'targets': []})

    @app.route('/scheduler/job/output', methods=['POST'])
    def output_route():  # pylint: disable=unused-variable
        if current_app.nr_output < 1:
            current_app.nr_output += 1
            return jsonify({'status': HTTPStatus.BAD_REQUEST, 'title': 'output upload failed'}), HTTPStatus.BAD_REQUEST

        return jsonify({'status': HTTPStatus.OK}), HTTPStatus.OK

    yield live_server(request, app, monkeypatch, pytestconfig)


# using direct call to supply custom app for live_server
@pytest.mark.filterwarnings('ignore:Fixture "live_server" called directly:DeprecationWarning')
def test_fail_server_communication(tmpworkdir, fail_server):  # pylint: disable=unused-argument,redefined-outer-name
    """tests failure handling while retrieving assignment or uploading output"""

    result = agent_main(['--server', fail_server.url(), '--debug', '--oneshot'])
    assert result == 0


def test_empty_server_communication(tmpworkdir, live_server):  # pylint: disable=unused-argument,redefined-outer-name
    """tests oneshot vs wait on assignment on empty server"""

    result = agent_main(['--server', live_server.url(), '--debug', '--oneshot'])
    assert result == 0

    proc_agent = multiprocessing.Process(target=agent_main, args=(['--server', live_server.url(), '--debug'],))
    proc_agent.start()
    sleep(2)
    assert proc_agent.pid
    assert proc_agent.is_alive()
    agent_main(['--terminate', str(proc_agent.pid)])
    proc_agent.join(3)
    assert not proc_agent.is_alive()
