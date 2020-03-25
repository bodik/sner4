# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

from ipaddress import ip_network

import pytest
from flask import url_for

from sner.server.scheduler.models import Excl, ExclFamily
from sner.server.utils import ExclMatcher, valid_next_url


def test_model_excl_validation():
    """test excl model validation"""

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family='invalid')
    assert str(pytest_wrapped_e.value) == 'Invalid family'

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family=ExclFamily.network, value='invalid')
    assert str(pytest_wrapped_e.value) == "'invalid' does not appear to be an IPv4 or IPv6 network"

    with pytest.raises(ValueError) as pytest_wrapped_e:
        Excl(family=ExclFamily.regex, value='invalid(')
    assert str(pytest_wrapped_e.value) == 'Invalid regex'

    test_excl = Excl(value='invalid(')
    with pytest.raises(ValueError):
        test_excl.family = ExclFamily.network
    with pytest.raises(ValueError):
        test_excl.family = ExclFamily.regex

    test_excl = Excl(family=ExclFamily.network)
    with pytest.raises(ValueError):
        test_excl.value = 'invalid('
    test_excl = Excl(family=ExclFamily.regex)
    with pytest.raises(ValueError):
        test_excl.value = 'invalid('


def test_excl_matcher(app, test_excl_network, test_excl_regex):  # pylint: disable=unused-argument
    """test matcher"""

    matcher = ExclMatcher()
    test_network = ip_network(test_excl_network.value)

    assert matcher.match(str(test_network.network_address))
    assert matcher.match(str(test_network.broadcast_address))
    assert not matcher.match(str(test_network.network_address-1))
    assert not matcher.match(str(test_network.broadcast_address+1))

    assert matcher.match('tcp://%s:12345' % str(test_network.network_address))
    assert not matcher.match('tcp://notanaddress:12345')

    assert matcher.match('notarget1')
    assert not matcher.match('notarget3')


def test_valid_next_url(app):  # pylint: disable=unused-argument
    """test next= and return_url= validator"""

    assert valid_next_url(url_for('index_route'))
    assert not valid_next_url('http://invalid_route')
    assert not valid_next_url('invalid_route')
