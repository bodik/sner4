# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
agent module six_enum_discover
"""

import json
import os
from uuid import uuid4

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """six_enum_discover test"""

    test_a = {'id': str(uuid4()), 'config': {'module': 'six_enum_discover', 'rate': 100}, 'targets': ['::0', '::1']}

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])

    # travis does not support ipv6 on bionic
    if 'TRAVIS' in os.environ:
        assert result == 1
        return

    assert result == 0
    assert '::1' in file_from_zip(f'{test_a["id"]}.zip', 'output-1.txt').decode('utf-8')
