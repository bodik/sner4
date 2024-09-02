# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
icmp_up plugin agent tests
"""

import json
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """jarm module execution test"""

    test_a = {
        'id': str(uuid4()),
        'config': {'module': 'icmp_up', 'args': '-w 3'},
        'targets': ['127.0.0.1', '::1', '999.999.999.999']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0

    assert '127.0.0.1 UP' in file_from_zip(f'{test_a["id"]}.zip', 'output').decode('utf-8')
    assert '::1 UP' in file_from_zip(f'{test_a["id"]}.zip', 'output').decode('utf-8')
    assert '999.999.999.999 DOWN' in file_from_zip(f'{test_a["id"]}.zip', 'output').decode('utf-8')
