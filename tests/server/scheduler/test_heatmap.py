# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.heatmap tests
"""

import json

from sner.server.scheduler.heatmap import Heatmap


def test_heatmap(app):  # pylint: disable=unused-argument
    """test heatmap"""

    heatmap = Heatmap()
    heatmap.put('hashval')
    heatmap.save()
    assert json.loads(heatmap.path.read_text(encoding='utf-8')) == {'hashval': 1}

    heatmap.pop('hashval')
    heatmap.save()
    assert json.loads(heatmap.path.read_text(encoding='utf-8')) == {}


def test_heatmap_hashval():
    """test heatmap"""

    assert Heatmap.hashval('127.0.0.1') == '127.0.0.0/24'
    assert Heatmap.hashval('2001:db8:aa::1:2:3:4') == '2001:db8:aa::/48'
    assert Heatmap.hashval('url') == 'url'
