# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core tests
"""

import pytest
import yaml
from flask import current_app

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
    SixDiscoQueueHandler,
    StorageSixEnum,
    Stage,
    StorageCleanup,
    StorageLoader,
    StorageLoaderQueueHandler,
    StorageRescan,
    WiringError
)
from sner.server.scheduler.core import JobManager
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Note, Service


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
  stage_storageloader:
    _class: StorageLoader

  stage_broken:
    _class: StorageLoaderQueueHandler
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
  stage_storageloader:
    _class: StorageLoader

  stage_standalonequeues:
    _class: StorageLoaderQueueHandler
    queues:
      - 'sner nmap script'
  stage_servicescan:
    _class: StorageLoaderQueueHandler
    queues:
      - 'sner servicescan nmap version'
      - 'sner servicescan jarm'

  stage_servicedisco:
    _class: ServiceDisco
    queues:
      - 'sner servicedisco nmap'

  stage_sixenumdisco:
    _class: SixDiscoQueueHandler
    queues:
      - 'sner six_enum_discover'

  stage_sixdnsdisco:
    _class: SixDiscoQueueHandler
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
    planner.autowire('stage_storageloader', StorageLoader)
    planner.autowire('stage_finalqueue', StorageLoaderQueueHandler, queues=[queue.name])

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

    SixDiscoQueueHandler([job_completed_sixenumdiscover.queue.name], stage_servicedisco, filter_nets=['127.0.0.0/24', '::1/128']).run()

    assert stage_servicedisco.task_count == 1
    assert '::1' in stage_servicedisco.task_args


def test_servicedisco(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test ServiceDisco"""

    stage_servicescan = DummyStage()

    ServiceDisco([job_completed_nmap.queue.name], stage_servicescan).run()

    assert stage_servicescan.task_count == 1
    assert 'tcp://127.0.0.1:139' in stage_servicescan.task_args


def test_storageloaderqueuehandler_task(app, queue, job_completed_nmap, target_factory):  # pylint: disable=unused-argument
    """test StorageLoaderQueueHandler base class"""

    stage_storageloader = DummyStage()

    # test QueueHandler init
    with pytest.raises(WiringError):
        StorageLoaderQueueHandler(['notexist'], stage_storageloader)

    # test QueueHandler task
    target_factory.create(queue=queue, target='target1')
    StorageLoaderQueueHandler([queue.name], stage_storageloader).task(['target1', 'target2'])
    assert Target.query.filter(Target.queue == queue).count() == 2

    # test QueueHandler run
    stage_storageloader = DummyStage()
    StorageLoaderQueueHandler([job_completed_nmap.queue.name], stage_storageloader).run()
    assert stage_storageloader.task_count == 1
    assert isinstance(stage_storageloader.task_args, ParsedItemsDb)


def test_storageloader(app, job_completed_nmap):  # pylint: disable=unused-argument
    """test test_stage_StandaloneQueues"""

    StorageLoader().task(JobManager.parse(job_completed_nmap))

    assert Host.query.count() == 1
    assert Service.query.count() == 5
    assert Note.query.count() == 17


def test_storagecleanup(app, host_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    StorageCleanup().run()
    assert Host.query.count() == 0
