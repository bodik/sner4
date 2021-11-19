# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

from ipaddress import ip_network

import pytest
from flask import url_for

from sner.server.extensions import db
from sner.server.scheduler.models import Excl, ExclFamily
from sner.server.utils import ExclMatcher, valid_next_url, windowed_query


def test_model_excl_validation():
    """test excl model validation"""

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family='invalid')
    assert str(pytest_wrapped_e.value) == 'Invalid family'

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family=ExclFamily.NETWORK, value='invalid')
    assert str(pytest_wrapped_e.value) == "'invalid' does not appear to be an IPv4 or IPv6 network"

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family=ExclFamily.REGEX, value='invalid(')
    assert str(pytest_wrapped_e.value) == 'Invalid regex'

    test_excl = Excl(value='invalid(')
    with pytest.raises(ValueError):
        test_excl.family = ExclFamily.NETWORK
    with pytest.raises(ValueError):
        test_excl.family = ExclFamily.REGEX

    test_excl = Excl(family=ExclFamily.NETWORK)
    with pytest.raises(ValueError):
        test_excl.value = 'invalid('
    test_excl = Excl(family=ExclFamily.REGEX)
    with pytest.raises(ValueError):
        test_excl.value = 'invalid('


def test_excl_matcher(app, excl_network, excl_regex):  # pylint: disable=unused-argument
    """test matcher"""

    matcher = ExclMatcher()
    tnetwork = ip_network(excl_network.value)

    assert matcher.match(str(tnetwork.network_address))
    assert matcher.match(str(tnetwork.broadcast_address))
    assert not matcher.match(str(tnetwork.network_address-1))
    assert not matcher.match(str(tnetwork.broadcast_address+1))

    assert matcher.match(f'tcp://{tnetwork.network_address}:12345')
    assert not matcher.match('tcp://notanaddress:12345')

    assert matcher.match('notarget1')
    assert not matcher.match('notarget3')


def test_valid_next_url(app):  # pylint: disable=unused-argument
    """test next= and return_url= validator"""

    assert valid_next_url(url_for('index_route'))
    assert not valid_next_url('http://invalid_route')
    assert not valid_next_url('invalid_route')


def test_windowed_query(app, excl_network):  # pylint: disable=unused-argument
    """test windowed query"""

    assert list(windowed_query(Excl.query, Excl.id, 1))
    assert list(windowed_query(db.session.query(Excl.id, Excl.id).select_from(Excl), Excl.id, 1))
