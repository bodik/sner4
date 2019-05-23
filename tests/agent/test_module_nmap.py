"""agent module dummy tests"""

import json
import os
import shutil
from uuid import uuid4

import pytest

from sner.agent import main


@pytest.fixture
def test_nmap_assignment():
    """nmap module assignment"""

    assignment = {'id': str(uuid4()), 'module': 'nmap', 'params': '-sL', 'targets': ['127.0.0.1']}
    yield assignment
    if os.path.exists(assignment['id']):
        shutil.rmtree(assignment['id'])


def test_basic(test_nmap_assignment):  # pylint: disable=redefined-outer-name
    """nmap module execution test"""

    result = main(['--assignment', json.dumps(test_nmap_assignment), '--debug'])
    assert result == 0
    assert os.path.exists('%s/output.gnmap' % test_nmap_assignment['id'])
    with open('%s/output.gnmap' % test_nmap_assignment['id'], 'r') as ftmp:
        assert 'Host: 127.0.0.1 (localhost)' in ftmp.read()
