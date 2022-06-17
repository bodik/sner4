# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler core tests
"""

from ipaddress import ip_network

import pytest

from sner.server.extensions import db
from sner.server.scheduler.core import ExclMatcher, SchedulerService
from sner.server.scheduler.models import Excl, ExclFamily, Heatmap, Readynet


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


def test_schedulerservice_hashval():
    """test heatmap hashval computation"""

    assert SchedulerService.hashval('127.0.0.1') == '127.0.0.0/24'
    assert SchedulerService.hashval('2001:db8:aa::1:2:3:4') == '2001:db8:aa::/48'
    assert SchedulerService.hashval('url') == 'url'
    assert SchedulerService.hashval('tcp://127.0.0.3:11') == '127.0.0.0/24'
    assert SchedulerService.hashval('tcp://[::1]:11') == '::/48'


def test_schedulerservice_readynetupdates(app, queue, target_factory):  # pylint: disable=unused-argument
    """test scheduler service readynet manipulation"""

    queue.group_size = 2
    target_factory.create(queue=queue, target='1', hashval=SchedulerService.hashval('1'))
    target_factory.create(queue=queue, target='2', hashval=SchedulerService.hashval('2'))
    target_factory.create(queue=queue, target='3', hashval=SchedulerService.hashval('3'))
    db.session.commit()

    assignment = SchedulerService.job_assign(None, [])

    assert len(assignment['targets']) == 2
    assert Readynet.query.count() == 1


def test_schedulerservice_hashvalprocessing(app, queue, target_factory):  # pylint: disable=unused-argument
    """test scheduler service hashvalsreadynet manipulation"""

    target_factory.create(queue=queue, target='tcp://127.0.0.1:22', hashval=SchedulerService.hashval('tcp://127.0.0.1:22'))
    db.session.commit()

    assignment = SchedulerService.job_assign(None, [])

    assert assignment
    assert Heatmap.query.one().hashval == '127.0.0.0/24'
