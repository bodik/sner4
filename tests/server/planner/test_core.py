# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core tests
"""

import logging
import os
from ipaddress import ip_address
from pathlib import Path

import pytest
import yaml

from sner.server.extensions import db
from sner.server.planner.core import (
    DummyStage,
    filter_external_hosts,
    filter_tarpits,
    NetlistEnum,
    Planner,
    project_hosts,
    project_services,
    project_sixenum_targets,
    ServiceDisco,
    SixDisco,
    StorageSixEnum,
    StorageCleanup,
    StorageLoader,
    StorageRescan
)
from sner.server.scheduler.core import SchedulerService
from sner.server.scheduler.models import Job, Target
from sner.server.storage.models import Host, Note, Service
from sner.server.utils import yaml_dump


def test_project_hosts(sample_pidb):
    """test project host"""

    hosts = project_hosts(sample_pidb)
    assert sorted(hosts) == sorted(['127.0.3.1', '127.0.4.1'])


def test_project_services(sample_pidb):
    """test project servicelist"""

    services = project_services(sample_pidb)
    assert len(services) == 202


def test_project_sixenum_targets():
    """test project_v6_enums"""

    enums = project_sixenum_targets(['::1', '2001:db8:0:0:0:00ff:fe00:0'])
    assert enums == ['sixenum://0000:0000:0000:0000:0000:0000:0000:0-ffff']


def test_filter_external_hosts():
    """test filter_nets"""

    hosts = filter_external_hosts(['127.0.0.1', '127.0.1.1'], ['127.0.0.0/24'])
    assert hosts == ['127.0.0.1']


def test_filter_tarpits(sample_pidb):
    """test filter_tarpits"""

    pidb = filter_tarpits(sample_pidb)
    assert len(pidb.hosts) == 1
    assert len(pidb.services) == 1


def test_netlistenum(app):  # pylint: disable=unused-argument
    """test NetlistEnum"""

    dummy = DummyStage()
    NetlistEnum('600s', ['127.0.0.0/31'], [dummy]).run()
    # trigger schedule timing code, must not affect output stages
    NetlistEnum('600s', ['127.0.0.0/31'], [dummy]).run()

    assert dummy.task_count == 1
    assert dummy.task_args == ['127.0.0.0', '127.0.0.1']


def test_storagesixenum(app, host_factory):  # pylint: disable=unused-argument
    """test StorageSixEnum"""

    host_factory.create(address='2001:DB8:aa::')
    host_factory.create(address='2001:DB8:bb::')
    dummy = DummyStage()
    StorageSixEnum('0s', dummy).run()

    expected = ['sixenum://2001:0db8:00aa:0000:0000:0000:0000:0-ffff', 'sixenum://2001:0db8:00bb:0000:0000:0000:0000:0-ffff']
    assert sorted(dummy.task_args) == sorted(expected)


def test_storagerescan(app, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline"""

    service_factory.create(host=host_factory.create(address='127.0.0.1'))
    service_factory.create(host=host_factory.create(address='::1'))
    sdisco_dummy = DummyStage()
    sscan_dummy = DummyStage()
    StorageRescan('0s', '0s', sdisco_dummy, '0s', [sscan_dummy]).run()

    assert len(sdisco_dummy.task_args) == 2
    assert len(sscan_dummy.task_args) == 2


def test_sixdiscoqueuehandler(app, job_completed_sixenumdiscover):  # pylint: disable=unused-argument
    """test SixDiscoQueueHandle"""

    dummy = DummyStage()
    SixDisco(job_completed_sixenumdiscover.queue.name, dummy, ['127.0.0.0/24', '::1/128']).run()

    assert dummy.task_count == 1
    assert '::1' in dummy.task_args


def test_servicedisco(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test ServiceDisco"""

    dummy = DummyStage()
    ServiceDisco(job_completed_nmap.queue.name, [dummy]).run()

    assert dummy.task_count == 1
    assert len(dummy.task_args) == 5
    assert 'tcp://127.0.0.1:139' in dummy.task_args


def test_storageloader(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test test_stage_StandaloneQueues"""

    StorageLoader(job_completed_nmap.queue.name).run()

    assert Host.query.count() == 1
    assert Service.query.count() == 6
    assert Note.query.count() == 17


def test_storageloader_invalidjobs(app, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test StorageLoader planner stage"""

    queue = queue_factory.create(name='test queue', config=yaml_dump({'module': 'dummy'}))
    job = job_completed_factory.create(queue=queue, make_output=Path('tests/server/data/parser-dummy-job-invalidjson.zip').read_bytes())
    job_completed_factory.create(queue=queue, make_output=Path('tests/server/data/parser-dummy-job.zip').read_bytes())
    assert Job.query.count() == 2

    dummy = DummyStage()
    ServiceDisco(queue.name, [dummy]).run()

    assert job.retval == 1000
    assert Job.query.count() == 1


def test_queuehandler_nxqueue(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test exception handling"""

    with pytest.raises(ValueError):
        StorageLoader('nx queue')


def test_storagecleanup(app, host_factory, service_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    service_factory.create(state='closed:test')
    StorageCleanup().run()

    assert Service.query.count() == 0
    assert Host.query.count() == 1


def test_planner_simple(app, queue_factory):  # pylint: disable=unused-argument
    """try somewhat default config"""

    queue_factory.create(name='sner nmap serviceversion')
    queue_factory.create(name='sner nmap servicedisco')
    queue_factory.create(name='sner six_dns_discover')
    queue_factory.create(name='sner six_enum_discover')

    config = yaml.safe_load("""
home_netranges_ipv4: []
home_netranges_ipv6: ['::1/128']

stage:
  service_scan:
    queues:
      - 'sner nmap serviceversion'

  service_disco:
    queue: 'sner nmap servicedisco'

  six_dns_disco:
    queue: 'sner six_dns_discover'

  six_enum_disco:
    queue: 'sner six_enum_discover'

  netlist_enum:
    schedule: 120days

  storage_six_enum:
    schedule: 90days

  storage_rescan:
    schedule: 1hour
    host_interval: 60days
    service_interval: 20days
""")

    planner = Planner(config, oneshot=True)
    planner.run()


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='large dataset test is slow')
def test_storagerescan_largedataset(runner, queue_factory, host_factory):  # pylint: disable=unused-argument
    """test StorageRescan with large dataset"""

    logger = logging.getLogger(__name__)

    logger.info('lot_of_targets prepare start')
    queue = queue_factory.create(name='queue1', config=yaml_dump({'module': 'nmap', 'args': 'arg1'}))
    existing_targets_count = 10**6
    existings_targets_vals = [
        str((queue.id, str(ip_address(idx)), SchedulerService.hashval(str(ip_address(idx)))))
        for idx in range(existing_targets_count)
    ]
    # bypass all db layers for performance
    query = 'INSERT INTO target (queue_id, target, hashval) VALUES ' + ','.join(existings_targets_vals)
    db.session.execute(query)
    logger.info('lot_of_targets prepare end')

    logger.info('lot_of_services prepare start')
    for addr in range(10):
        host = host_factory.create(address=str(ip_address(addr)))
        # bypass all db layers for performance
        query = 'INSERT INTO service (host_id, proto, port, tags) VALUES ' + ','.join([str((host.id, 'tcp', str(idx), '{}')) for idx in range(64000)])
        db.session.execute(query)
        logging.info('prepared %s', host)
    logger.info('lot_of_services prepare end')

    db.session.expire_all()

    dummy = ServiceDisco('queue1', [DummyStage()])
    StorageRescan('0s', '0s', dummy, '0s', [dummy]).run()

    assert Target.query.count() == existing_targets_count + Service.query.count()
