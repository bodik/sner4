# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler core tests
"""

from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService
from sner.server.scheduler.models import Readynet


def test_schedulerservice_hashval():
    """test heatmap hashval computation"""

    assert SchedulerService.hashval('127.0.0.1') == '127.0.0.0/24'
    assert SchedulerService.hashval('2001:db8:aa::1:2:3:4') == '2001:db8:aa::/48'
    assert SchedulerService.hashval('url') == 'url'


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
