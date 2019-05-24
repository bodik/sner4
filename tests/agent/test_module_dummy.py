"""agent module dummy tests"""

import json
import os
import shutil
from uuid import uuid4

import pytest

from sner.agent import main as agent_main


@pytest.fixture
def test_dummy_assignment():
    """dummy module assignment"""

    assignment = {'id': str(uuid4()), 'module': 'dummy', 'params': '--static_assignment', 'targets': ['target1']}
    yield assignment
    if os.path.exists(assignment['id']):
        shutil.rmtree(assignment['id'])


def test_basic(test_dummy_assignment):  # pylint: disable=redefined-outer-name
    """dummy module execution test"""

    result = agent_main(['--assignment', json.dumps(test_dummy_assignment), '--debug'])
    assert result == 0
    assert os.path.exists('%s/assignment.json' % test_dummy_assignment['id'])
    with open('%s/assignment.json' % test_dummy_assignment['id'], 'r') as ftmp:
        assert test_dummy_assignment['targets'][0] in ftmp.read()
