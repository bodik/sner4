"""agent module dummy tests"""

import json
import os
from uuid import uuid4

from sner.agent import main as agent_main


def test_basic(tmpworkdir):
    """nmap module execution test"""

    test_a = {'id': str(uuid4()), 'module': 'nmap', 'params': '-sL', 'targets': ['127.0.0.1']}

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0
    assert os.path.exists('%s/output.gnmap' % test_a['id'])
    with open('%s/output.gnmap' % test_a['id'], 'r') as ftmp:
        assert 'Host: 127.0.0.1 (localhost)' in ftmp.read()
