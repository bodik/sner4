# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module dummy tests
"""

import json
from uuid import uuid4

from sner.agent import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """nmap module execution test"""

    test_a = {'id': str(uuid4()), 'config': {'module': 'nmap', 'args': '-sL', 'timing_perhost': 1}, 'targets': ['127.0.0.1']}

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0
    assert 'Host: 127.0.0.1 (localhost)' in file_from_zip('%s.zip' % test_a['id'], 'output.gnmap').decode('utf-8')
