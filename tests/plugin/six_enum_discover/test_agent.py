# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
six_enum_discover plugin agent tests
"""

import json
import os
from socket import AF_INET6
from uuid import uuid4

import pytest
from pyroute2 import NDB

from sner.agent.core import main as agent_main
from sner.lib import file_from_zip
from sner.plugin.six_enum_discover.agent import AgentModule


def test_basic(tmpworkdir):  # pylint: disable=unused-argument
    """six_enum_discover test"""

    test_a = {
        'id': str(uuid4()),
        'config': {
            'module': 'six_enum_discover',
            'rate': 100
        },
        'targets': ['sixenum://::1-2', 'sixenum://::01']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])

    # no support for IPv6 in GH Actions
    if 'GITHUB_ACTIONS' in os.environ:
        assert result == 1
        return

    assert result == 0
    assert '::1' in file_from_zip(f'{test_a["id"]}.zip', 'output-0.txt').decode('utf-8')


def test_agent_enumeratetargets():
    """six_enum_discover enumerate targets test"""

    targets = list(AgentModule().enumerate_targets(['sixenum://::1', 'sixenum://::1-2', 'sixenum://::01', '2001:db8:bb::1:2:3:0-ffff']))
    assert targets == [(0, '::1'), (1, '::1-2'), (2, '::01')]


@pytest.mark.skipif('PYTEST_IPV6' not in os.environ, reason='ipv6 requires global connectivity')
def test_enum_simple(tmpworkdir):  # pylint: disable=unused-argument
    """
    six_enum_discover test for LAN

    scan6 does not correctly work for remote address scanning, when running towards local LAN
    (https://github.com/fgont/ipv6toolkit/issues/41). the test triggers the detection part
    of six_enum_discover._is_localnet() which cannot run in CI because it lacks IPv6 support.
    also scan6 will not report self address, hence the test checks only number of items.
    """

    addr = list(filter(lambda x: x.family == AF_INET6 and x.scope == 0, NDB().addresses.dump()))
    assert addr, 'No IPv6 address found'
    addr = addr[0].address

    test_a = {
        'id': str(uuid4()),
        'config': {
            'module': 'six_enum_discover',
            'rate': 100
        },
        'targets': [f'sixenum://{addr}']
    }

    result = agent_main(['--assignment', json.dumps(test_a), '--debug'])
    assert result == 0

    data = file_from_zip(f'{test_a["id"]}.zip', 'output-0.txt').decode('utf-8')
    assert len(data.splitlines()) > 1
