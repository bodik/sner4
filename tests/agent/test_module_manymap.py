# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module manymap tests
"""

import json
from uuid import uuid4

from sner.agent import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """manymap module execution test"""

    test_a = {'id': str(uuid4()), 'module': 'manymap', 'params': '-sV', 'targets': ['invalid', 'tcp://127.0.0.1:1', 'udp://[::1]:2']}

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0
    assert 'Host: 127.0.0.1 (localhost)' in file_from_zip('%s.zip' % test_a['id'], 'output-1.gnmap').decode('utf-8')
    assert '# Nmap done at' in file_from_zip('%s.zip' % test_a['id'], 'output-2.gnmap').decode('utf-8')
