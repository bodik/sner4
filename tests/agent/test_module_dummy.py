"""agent module dummy tests"""

import json
import os

from sner.agent import main as agent_main


def test_basic(tmpworkdir, test_dummy_a):
    """dummy module execution test"""

    result = agent_main(['--assignment', json.dumps(test_dummy_a), '--debug'])
    assert result == 0
    assert os.path.exists('%s/assignment.json' % test_dummy_a['id'])
    with open('%s/assignment.json' % test_dummy_a['id'], 'r') as ftmp:
        assert test_dummy_a['targets'][0] in ftmp.read()
