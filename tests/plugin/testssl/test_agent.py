# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
testssl plugin agent tests
"""

import json
import os
import ssl
from uuid import uuid4

import pytest
from pytest_httpserver.httpserver import HTTPServer
from werkzeug.serving import make_ssl_devcert

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip
import sner.plugin.testssl.agent  # noqa: F401  pylint: disable=unused-import  ; triggers coverage for module imports when not PYTEST_SLOW


@pytest.fixture
def https_server(tmpworkdir):
    """
    HTTPS server fixture dubbed from pytest-httpserver.
    The original fixture does not work in conjunction with function scoped tmpworkdir fixture.
    """

    cert, key = make_ssl_devcert('testcert')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)

    server = HTTPServer(ssl_context=context)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='testssl tool is slow')
def test_basic(tmpworkdir, https_server):  # pylint: disable=unused-argument
    """testssl module execution test"""

    https_server.expect_request('/').respond_with_data("Hello world!", content_type="text/plain")

    test_a = {
        'id': str(uuid4()),
        'config': {'module': 'testssl', 'delay': 0},
        'targets': ['udp://127.0.0.1:1', f'tcp://127.0.0.1:{https_server.port}']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0

    results = json.loads(file_from_zip(f'{test_a["id"]}.zip', 'output-1.json'))
    assert results
    assert type(results['scanTime']) is int
