# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module nmap tests
"""

import json
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """jarm module execution test"""

    test_a = {
        'id': str(uuid4()),
        'config': {'module': 'jarm', 'delay': 0},
        'targets': ['tcp://127.0.0.1:1', 'udp://127.0.0.1:1']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0
    assert \
        'JARM: 00000000000000000000000000000000000000000000000000000000000000' \
        in file_from_zip(f'{test_a["id"]}.zip', 'output-0.out').decode('utf-8')
