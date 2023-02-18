# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
screenshot_web plugin agent tests
"""

import json
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


class ScreenshotServer():
    """screenshot_web test server"""

    def __init__(self, server):
        self.server = server
        self.server.expect_request('/').respond_with_handler(self.handler)

    def handler(self, request):
        """handle request"""
        return '<h1>hello world</h1>'


def test_basic(tmpworkdir, httpserver):  # pylint: disable=unused-argument
    """screenshot_web module execution test"""

    sserver = ScreenshotServer(httpserver)

    test_a = {
        'id': str(uuid4()),
        'config': {'module': 'screenshot_web', 'delay': 0, 'geometry': '640,480'},
        'targets': [f'tcp://127.0.0.1:{sserver.server.port} http://localhost:{sserver.server.port}']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0

    results = json.loads(file_from_zip(f'{test_a["id"]}.zip', 'results.json'))
    assert results
    assert file_from_zip(f'{test_a["id"]}.zip', list(results.keys())[0])
