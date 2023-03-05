# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler core tests
"""

from ipaddress import ip_address, ip_network

import pytest
import yaml
from flask import current_app

from sner.server.extensions import db
from sner.server.scheduler.core import ExclMatcher, SchedulerService
from sner.server.scheduler.models import Excl, ExclFamily, Heatmap, Job, Readynet


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


def test_excl_matcher(app):  # pylint: disable=unused-argument
    """test matcher"""

    test_regex = 'notarget[012]'
    test_network = '127.66.66.0/26'

    matcher = ExclMatcher(yaml.safe_load(f"""
        - [regex, '{test_regex}']
        - [network, '{test_network}']
    """))
    tnetwork = ip_network(test_network)

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


def test_schedulerservice_morereadynetupdates(app, queue, target_factory):  # pylint: disable=unused-argument
    """
    test scheduler service readynet manipulation

    used to analyze and reason about heatmap_pop readynet sql queries for update readynet lists.
    using readynet updates `if heat < level` provides automatic updates for readynets when hot_level changes
    in runtime, but produces extra queries for every returning job. result: on hot_level change
    readynets map must be manually recounted.
    """

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 5
    queue.group_size = 2

    for addr in range(10):
        tmp = str(ip_address(addr))
        target_factory.create(queue=queue, target=tmp, hashval=SchedulerService.hashval(tmp))
    db.session.commit()

    assignment1 = SchedulerService.job_assign(None, [])
    assignment2 = SchedulerService.job_assign(None, [])
    assignment3 = SchedulerService.job_assign(None, [])

    assert len(assignment3['targets']) == 1
    assert Readynet.query.count() == 0

    SchedulerService.job_output(Job.query.get(assignment3['id']), 0, b'')
    assert Readynet.query.count() == 1

    SchedulerService.job_output(Job.query.get(assignment2['id']), 0, b'')
    SchedulerService.job_output(Job.query.get(assignment1['id']), 0, b'')
    assert Readynet.query.count() == 1


def test_schedulerservice_hashvalprocessing(app, queue, target_factory):  # pylint: disable=unused-argument
    """test scheduler service hashvalsreadynet manipulation"""

    target_factory.create(queue=queue, target='tcp://127.0.0.1:23', hashval=SchedulerService.hashval('tcp://127.0.0.1:23'))
    db.session.commit()

    assignment = SchedulerService.job_assign(None, [])

    assert assignment
    assert Heatmap.query.one().hashval == '127.0.0.0/24'


def test_schedulerservice_readynetrecount(app, queue, target_factory):  # pylint: disable=unused-argument
    """test scheduler service readynet_recount"""

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 5
    queue.group_size = 2

    for addr in range(10):
        tmp = str(ip_address(addr))
        target_factory.create(queue=queue, target=tmp, hashval=SchedulerService.hashval(tmp))
    db.session.commit()

    SchedulerService.job_assign(None, [])
    SchedulerService.job_assign(None, [])

    assignment3 = SchedulerService.job_assign(None, [])
    assert len(assignment3['targets']) == 1
    assert Readynet.query.count() == 0

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 7
    SchedulerService.readynet_recount()
    assert Readynet.query.count() == 1

    assignment4 = SchedulerService.job_assign(None, [])
    assert len(assignment4['targets']) == 2

    current_app.config['SNER_HEATMAP_HOT_LEVEL'] = 3
    SchedulerService.readynet_recount()
    assert Readynet.query.count() == 0
