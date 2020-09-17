# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module six_dns_discover
"""

import json
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """dix_dns_discover test"""

    test_a = {
        'id': str(uuid4()),
        'config': {
            'module': 'six_dns_discover',
            'delay': 1
        },
        'targets': ['127.0.0.1', '127.0.0.2']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0
    assert '::1' in json.loads(file_from_zip(f'{test_a["id"]}.zip', 'output.json').decode('utf-8'))
