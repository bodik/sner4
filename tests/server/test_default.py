# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

from ipaddress import ip_network

import pytest
from flask import url_for
from flask_wtf import FlaskForm

from sner.server.form import TextAreaListField
from sner.server.model.scheduler import Excl, ExclFamily
from sner.server.utils import ExclMatcher, valid_next_url
from tests.server import DummyPostData


def test_linesfield(app):  # pylint: disable=unused-argument
    """tests linefield custom form field"""

    class Xform(FlaskForm):
        """form test instance"""
        a = TextAreaListField()

    form = Xform(DummyPostData({'a': 'a\nb'}))
    assert isinstance(form.a.data, list)
    assert len(form.a.data) == 2

    form = Xform(DummyPostData())
    assert isinstance(form.a.data, list)
    assert not form.a.data


def test_models_auth_repr(app, test_user, test_wncred):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_user)
    assert repr(test_wncred)


def test_models_scheduler_repr(app, test_task, test_queue, test_target, test_job, test_excl_network):  # noqa: E501  pylint: disable=unused-argument,too-many-arguments
    """test models repr methods"""

    assert repr(test_task)
    assert repr(test_queue)
    assert repr(test_target)
    assert repr(test_job)
    assert repr(test_excl_network)


def test_models_storage_repr(app, test_host, test_service, test_vuln, test_note):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_host)
    assert repr(test_service)
    assert repr(test_vuln)
    assert repr(test_note)


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
