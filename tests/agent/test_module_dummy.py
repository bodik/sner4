# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module dummy tests
"""

import json

from sner.agent import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir, test_dummy_a):  # pylint: disable=unused-argument
    """dummy module execution test"""

    result = agent_main(['--assignment', json.dumps(test_dummy_a), '--debug'])
    assert result == 0
    assert test_dummy_a['targets'][0] in file_from_zip('%s.zip' % test_dummy_a['id'], 'assignment.json').decode('utf-8')
