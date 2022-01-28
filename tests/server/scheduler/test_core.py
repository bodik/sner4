# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler core tests
"""

from sner.server.scheduler.core import target_hashval


def test_target_hashval():
    """test heatmap hashval computation"""

    assert target_hashval('127.0.0.1') == '127.0.0.0/24'
    assert target_hashval('2001:db8:aa::1:2:3:4') == '2001:db8:aa::/48'
    assert target_hashval('url') == 'url'
