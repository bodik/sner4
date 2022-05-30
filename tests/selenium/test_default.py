# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium based UI tests
"""

from flask import url_for


def test_index_route(live_server, selenium):  # pylint: disable=unused-argument
    """very basic index hit test"""

    selenium.get(url_for('index_route', _external=True))
    assert 'Homepage - sner4' in selenium.title
