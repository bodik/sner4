# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

from flask import url_for

from sner.server.extensions import db
from sner.server.storage.models import Host
from sner.server.utils import valid_next_url, windowed_query


def test_valid_next_url(app):  # pylint: disable=unused-argument
    """test next= and return_url= validator"""

    assert valid_next_url(url_for('index_route'))
    assert not valid_next_url('http://invalid_route')
    assert not valid_next_url('invalid_route')


def test_windowed_query(app, host):  # pylint: disable=unused-argument
    """test windowed query"""

    assert list(windowed_query(Host.query, Host.id, 1))
    assert list(windowed_query(db.session.query(Host.id, Host.id).select_from(Host), Host.id, 1))
