# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nuclei plugin agent tests
"""

import json
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


class VulnerableServer():
    """vulnerable test server for nuclei"""
    def __init__(self, server):
        self.server = server
        self.server.expect_request('/download.php').respond_with_handler(self.handler)

    def handler(self, request):
        """handle request"""
        filename = request.args.get('file')

        if not filename:
            return 'File not found'

        return 'root:x:0:0:root:/root:/bin/bash'


def test_basic(tmpworkdir, httpserver):
    """nuclei module execution test"""

    vuln_server = VulnerableServer(httpserver)

    test_a = {
        'id': str(uuid4()),
        'config': {'module': 'nuclei', 'args': '-pt http -id flir-path-traversal'},
        'targets': [f'http://127.0.0.1:{vuln_server.server.port}']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0

    [report] = json.loads(file_from_zip(f'{test_a["id"]}.zip', 'output.json').decode('utf-8'))
    assert report['template-id'] == 'flir-path-traversal'
    assert report['info']['severity'] == 'high'
