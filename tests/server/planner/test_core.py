# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core tests
"""

import logging
import os
from ipaddress import ip_address

import pytest
import yaml
from flask import current_app

from sner.server.extensions import db
from sner.server.parser import ParsedItemsDb
from sner.server.planner.core import (
    DummyStage,
    filter_external_hosts,
    filter_tarpits,
    NetlistEnum,
    Planner,
    project_hosts,
    project_services,
    project_six_enums,
    ServiceDisco,
    SixDisco,
    StorageSixEnum,
    Stage,
    StorageCleanup,
    StorageImport,
    StorageLoader,
    StorageRescan,
    WiringError
)
from sner.server.scheduler.core import JobManager, SchedulerService
from sner.server.scheduler.models import Target
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


def test_project_six_enums():
    """test project_v6_enums"""

    enums = project_six_enums(['::1', '2001:db8:0:0:0:00ff:fe00:0'])
    assert enums == ['0000:0000:0000:0000:0000:0000:0000:0-ffff']


def test_filter_external_hosts():
    """test filter_nets"""

    hosts = filter_external_hosts(['127.0.0.1', '127.0.1.1'], ['127.0.0.0/24'])
    assert hosts == ['127.0.0.1']


def test_filter_tarpits(sample_pidb):
    """test filter_tarpits"""

    pidb = filter_tarpits(sample_pidb)

    assert len(pidb.hosts) == 1
    assert len(pidb.services) == 1


def test_planner_dummy(app):  # pylint: disable=unused-argument
    """dummy run"""

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
stages:
  stage_dummy:
    _class: DummyStage
""")

    planner = Planner(oneshot=True)
    planner.run()

    assert 'stage_dummy' in planner.stages
    assert planner.stages['stage_dummy'].run_count == 1
    assert planner.stages['stage_dummy'].task_count == 1
    assert planner.stages['stage_dummy'].task_args == 'dummy'


def test_planner_stageexception(app, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """planner stage exception"""

    queue = queue_factory.create(name='aqueue')
    job_completed_factory.create(queue=queue)

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
stages:
  stage_storageimport:
    _class: StorageImport

  stage_broken:
    _class: StorageLoader
    queues:
      - aqueue
""")

    planner = Planner(oneshot=True)
    # artificialy break stage to emit exception
    planner.stages['stage_broken'].stage_storageloader = None
    planner.run()


def test_planner_defaultconfig(app, queue_factory):  # pylint: disable=unused-argument
    """try somewhat default config"""

    queues = [
        'sner nmap script',
        'sner servicescan nmap version',
        'sner servicescan jarm',
        'sner servicedisco nmap',
        'sner six_enum_discover',
        'sner six_dns_discover',
    ]
    for queue in queues:
        queue_factory.create(name=queue)

    current_app.config['SNER_PLANNER'] = yaml.safe_load("""
common:
  home_netranges_ipv4: &home_netranges_ipv4 []
  home_netranges_ipv6: &home_netranges_ipv6 ['::1/128']

stages:
  # queue processors
  stage_storageimport:
    _class: StorageImport

  stage_standalonequeues:
    _class: StorageLoader
    queues:
      - 'sner nmap script'
  stage_servicescan:
    _class: StorageLoader
    queues:
      - 'sner servicescan nmap version'
      - 'sner servicescan jarm'

  stage_servicedisco:
    _class: ServiceDisco
    queues:
      - 'sner servicedisco nmap'

  stage_sixenumdisco:
    _class: SixDisco
    queues:
      - 'sner six_enum_discover'

  stage_sixdnsdisco:
    _class: SixDisco
    queues:
      - 'sner six_dns_discover'
    filter_nets: *home_netranges_ipv6

  # schedules
  stage_storagecleanup:
    _class: StorageCleanup

  stage_netlistenum:
    _class: NetlistEnum
    schedule: 120days
    netlist: *home_netranges_ipv4

  stage_storagesixenum:
    _class: StorageSixEnum
    schedule: 90days

  stage_storagerescan:
    _class: StorageRescan
    schedule: 1hour
    service_interval: 20days
    host_interval: 60days
""")

    planner = Planner(oneshot=True)
    planner.run()


def test_planner_autowiring_error(app):  # pylint: disable=unused-argument
    """dummy run"""

    planner = Planner(oneshot=True)
    with pytest.raises(WiringError):
        planner.autowire('dummy', Stage)


def test_planner_getwiring(app, queue):  # pylint: disable=unused-argument
    """dummy run"""

    planner = Planner(oneshot=True)
    planner.autowire('stage_storageimport', StorageImport)
    planner.autowire('stage_finalqueue', StorageLoader, queues=[queue.name])

    wiring = planner.get_wiring()
    assert len(wiring) == 2
    assert len(wiring[planner.stages['stage_finalqueue']]) == 1


def test_netlistenum(app):  # pylint: disable=unused-argument
    """test NetlistEnum"""

    stage_servicedisco = DummyStage()
    stage_sixdnsdisco = DummyStage()

    NetlistEnum('600s', ['127.0.0.0/31'], stage_servicedisco, stage_sixdnsdisco).run()
    # trigger schedule timing code, must not affect output stages
    NetlistEnum('600s', ['127.0.0.0/31'], stage_servicedisco, stage_sixdnsdisco).run()

    assert stage_servicedisco.task_count == 1
    assert stage_servicedisco.task_args == ['127.0.0.0', '127.0.0.1']
    assert stage_sixdnsdisco.task_count == 1
    assert stage_sixdnsdisco.task_args == ['127.0.0.0', '127.0.0.1']


def test_hostv6enum(app, host_factory):  # pylint: disable=unused-argument
    """test Hostv6Enum"""

    host_factory.create(address='2001:DB8:aa::')
    host_factory.create(address='2001:DB8:bb::')
    stage_sixenumdisco = DummyStage()

    StorageSixEnum('0s', stage_sixenumdisco).run()

    expected = ['2001:0db8:00aa:0000:0000:0000:0000:0-ffff', '2001:0db8:00bb:0000:0000:0000:0000:0-ffff']
    assert sorted(stage_sixenumdisco.task_args) == sorted(expected)


def test_storagerescan(app, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline"""

    service_factory.create(host=host_factory.create(address='127.0.0.1'))
    service_factory.create(host=host_factory.create(address='::1'))
    stage_servicescan = DummyStage()
    stage_servicedisco = DummyStage()

    StorageRescan('0s', '0s', '0s', stage_servicescan, stage_servicedisco).run()

    assert len(stage_servicedisco.task_args) == 2
    assert len(stage_servicescan.task_args) == 2


def test_sixdiscoqueuehandler(app, job_completed_sixenumdiscover):  # pylint: disable=unused-argument
    """test SixDiscoQueueHandle"""

    stage_servicedisco = DummyStage()

    SixDisco([job_completed_sixenumdiscover.queue.name], stage_servicedisco, filter_nets=['127.0.0.0/24', '::1/128']).run()

    assert stage_servicedisco.task_count == 1
    assert '::1' in stage_servicedisco.task_args


def test_servicedisco(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test ServiceDisco"""

    stage_servicescan = DummyStage()

    ServiceDisco([job_completed_nmap.queue.name], stage_servicescan).run()

    assert stage_servicescan.task_count == 1
    assert len(stage_servicescan.task_args) == 5
    assert 'tcp://127.0.0.1:139' in stage_servicescan.task_args


def test_storageloaderqueuehandler_task(app, queue, job_completed_nmap, target_factory):  # pylint: disable=unused-argument
    """test StorageLoader base class"""

    stage_storageimport = DummyStage()

    # test QueueHandler init
    with pytest.raises(WiringError):
        StorageLoader(['notexist'], stage_storageimport)

    # test QueueHandler task
    target_factory.create(queue=queue, target='target1')
    StorageLoader([queue.name], stage_storageimport).task(['target1', 'target2'])
    assert Target.query.filter(Target.queue == queue).count() == 2

    # test QueueHandler run
    stage_storageimport = DummyStage()
    StorageLoader([job_completed_nmap.queue.name], stage_storageimport).run()
    assert stage_storageimport.task_count == 1
    assert isinstance(stage_storageimport.task_args, ParsedItemsDb)


def test_storageloader(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test test_stage_StandaloneQueues"""

    StorageImport().task(JobManager.parse(job_completed_nmap))

    assert Host.query.count() == 1
    assert Service.query.count() == 6
    assert Note.query.count() == 17


def test_storagecleanup(app, host_factory, service_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    service_factory.create(state='closed:test')
    StorageCleanup().run()
    assert Service.query.count() == 0
    assert Host.query.count() == 1


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

    stage_servicescan = ServiceDisco(['queue1'], DummyStage())
    stage_servicedisco = ServiceDisco(['queue1'], DummyStage())
    StorageRescan('0s', '0s', '0s', stage_servicescan, stage_servicedisco).run()

    assert Target.query.count() == existing_targets_count + Service.query.count()
