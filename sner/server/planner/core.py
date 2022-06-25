# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core
"""

import inspect
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from ipaddress import ip_address, ip_network, IPv6Address
from pathlib import Path
from time import sleep

from flask import current_app
from pytimeparse import parse as timeparse
from sqlalchemy import select
from sqlalchemy.orm.exc import NoResultFound

from sner.lib import format_host_address, TerminateContextMixin
from sner.server.extensions import db
from sner.server.scheduler.core import enumerate_network, JobManager, QueueManager
from sner.server.scheduler.models import Queue, Job, Target
from sner.server.storage.core import StorageManager


REGISTERED_STAGES = {}


def register_stage(class_):
    """register stage class by name"""
    if class_.__name__ not in REGISTERED_STAGES:
        REGISTERED_STAGES[class_.__name__] = class_
    return class_


def project_hosts(pidb):
    """project host list from context data"""

    return [f'{host.address}' for host in pidb.hosts]


def project_services(pidb):
    """project service list from pidb"""

    return [
        f'{service.proto}://{format_host_address(pidb.hosts.by.iid[service.host_iid].address)}:{service.port}'
        for service
        in pidb.services
    ]


def project_six_enums(hosts):
    """project v6 enum patterns for agent"""

    targets = set()
    for host in hosts:
        exploded = IPv6Address(host).exploded
        # do not enumerate EUI-64 hosts/nets
        if exploded[27:32] == 'ff:fe':
            continue

        # generate mask for scan6 tool
        exploded = exploded.split(':')
        exploded[-1] = '0-ffff'
        target = ':'.join(exploded)

        targets.add(target)

    return list(targets)


def filter_external_hosts(hosts, nets):
    """filter addrs not belonging to nets list"""

    whitelist = [ip_network(net) for net in nets]
    return [item for item in hosts if any(ip_address(item) in net for net in whitelist)]


def filter_tarpits(pidb, threshold=200):
    """filter filter hosts with too much services detected"""

    host_services_count = defaultdict(int)
    for service in pidb.services:
        host_services_count[pidb.hosts.by.iid[service.host_iid].address] += 1
    hosts_over_threshold = dict(filter(lambda x: x[1] > threshold, host_services_count.items()))

    if hosts_over_threshold:
        for collection in ['services', 'vulns', 'notes']:
            # list() should provide copy for list-in-loop pruning
            for item in list(getattr(pidb, collection)):
                if pidb.hosts.by.iid[item.host_iid].address in hosts_over_threshold:
                    getattr(pidb, collection).remove(item)

        # list() should provide copy for list-in-loop pruning
        for host in list(pidb.hosts):
            if host.address in hosts_over_threshold:
                pidb.hosts.remove(host)

    return pidb


class WiringError(RuntimeError):
    """stage autowiring error"""


class Planner(TerminateContextMixin):
    """planner"""

    LOOPSLEEP = 60

    def __init__(self, oneshot=False):
        self.log = current_app.logger
        self.log.setLevel(logging.DEBUG if current_app.config['DEBUG'] else logging.INFO)
        self.original_signal_handlers = {}
        self.loop = None
        self.oneshot = oneshot
        self.stages = {}

        stages_config = deepcopy(current_app.config['SNER_PLANNER'].get('stages', {}))
        for name, kwargs in stages_config.items():  # reversed here preserves dependencies hierarchy
            class_ = REGISTERED_STAGES[kwargs.pop('_class')]
            self.autowire(name, class_, **kwargs)

    def autowire(self, name, class_, **kwargs):
        """
        introspection name-based autowiring stage registration routine
        inspired by https://github.com/kodemore/kink, but does not use globals for container runtime
        """

        resolved_kwargs = kwargs
        for pname in inspect.signature(class_).parameters:
            if (pname not in resolved_kwargs) and (pname in self.stages):
                resolved_kwargs[pname] = self.stages[pname]

        try:
            self.stages[name] = class_(**resolved_kwargs)
        except TypeError as exc:
            self.log.error('autowiring error stage: %s class:%s resolved_kwargs:%s', name, class_.__name__, resolved_kwargs)
            self.log.error(str(exc))
            raise WiringError('autowiring error') from None

    def get_wiring(self):
        """analyze stages in current container"""

        graph = {}
        for stage in self.stages.values():
            deps = []
            for pname in inspect.signature(stage.__class__).parameters:
                if pname in self.stages:
                    deps.append(self.stages[pname])
            graph[stage] = deps

        return graph

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """terminate at once"""

        self.log.info('terminate')
        self.loop = False

    def run(self):
        """run planner loop"""

        self.log.info('startup')
        self.loop = True

        with self.terminate_context():
            while self.loop:
                for name, stage in self.stages.items():
                    try:
                        current_app.logger.debug(f'stage run {name} {stage}')
                        stage.run()
                    except Exception as exc:  # pylint: disable=broad-except  ; any exception can be raised during stage processing
                        current_app.logger.error(f'stage failed, {name} {stage}, {exc}', exc_info=True)

                if self.oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    # support for long loops, but allow fast shutdown
                    for _ in range(self.LOOPSLEEP):
                        if self.loop:
                            sleep(1)


class Stage(ABC):
    """planner stage base"""

    @abstractmethod
    def task(self, data):
        """incoming event handler"""

    @abstractmethod
    def run(self):
        """stage main runnable"""


class Schedule(Stage):
    """schedule base"""

    def __init__(self, schedule):
        self.schedule = schedule
        self.lastrun_path = Path(f'{current_app.config["SNER_VAR"]}/lastrun.{self.__class__.__name__}')

    def task(self, data):
        """dummy"""

    def run(self):
        """run only on configured schedule"""

        if self.lastrun_path.exists():
            lastrun = datetime.fromisoformat(self.lastrun_path.read_text(encoding='utf8'))
            if (datetime.utcnow().timestamp() - lastrun.timestamp()) < timeparse(self.schedule):
                return

        self._run()
        self.lastrun_path.write_text(datetime.utcnow().isoformat(), encoding='utf8')

    @abstractmethod
    def _run(self):
        """stage runnable implementation"""


class QueueHandler(Stage):
    """queue handler base"""

    def __init__(self, queues):
        self.queues = queues
        for queue in self.queues:
            try:
                Queue.query.filter(Queue.name == queue).one()
            except NoResultFound:
                raise WiringError(f'missing queue "{queue}"') from None

    def _drain(self):
        """drain queues and yield PIDBs"""

        for queue in Queue.query.filter(Queue.name.in_(self.queues)).all():
            for aajob in Job.query.filter(Job.queue_id == queue.id, Job.retval == 0).all():
                current_app.logger.info(f'{self.__class__.__name__} drain {aajob.id} ({aajob.queue.name})')
                yield JobManager.parse(aajob)
                JobManager.archive(aajob)
                JobManager.delete(aajob)

    def task(self, data):
        """enqueue data/targets into all configured queues"""

        for queue in Queue.query.filter(Queue.name.in_(self.queues)).all():
            already_queued = db.session.connection().execute(select(Target.target).filter(Target.queue == queue)).scalars().all()
            enqueue = list(set(data) - set(already_queued))
            QueueManager.enqueue(queue, enqueue)
            current_app.logger.info(f'{self.__class__.__name__} enqueued {len(enqueue)} targets to "{queue.name}"')


@register_stage
class DummyStage(Stage):
    """dummy testing stage"""

    def __init__(self):
        self.task_count = 0
        self.task_args = None
        self.run_count = 0
        self.run_args = None

    def task(self, data):
        self.task_count += 1
        self.task_args = data

    def run(self):
        self.task('dummy')
        self.run_count += 1


@register_stage
class StorageImport(Stage):
    """final stage, imports data to storage"""

    def task(self, data):
        """imports data to storage"""

        StorageManager.import_parsed(data)

    def run(self):
        """dummy"""


@register_stage
class StorageCleanup(Stage):
    """cleanup storage"""

    def task(self, data):
        """dummy"""

    def run(self):
        """cleanup storage"""

        StorageManager.cleanup_storage()
        current_app.logger.debug(f'{self.__class__.__name__} finished')


@register_stage
class DummySchedule(Schedule):
    """dummy testing schedule"""

    def _run(self):
        """dummy"""


@register_stage
class NetlistEnum(Schedule):
    """periodic host discovery via list of ipv4 networks"""

    def __init__(self, schedule, netlist, stage_servicedisco, stage_sixdnsdisco):
        super().__init__(schedule)
        self.netlist = netlist
        self.stage_servicedisco = stage_servicedisco
        self.stage_sixdnsdisco = stage_sixdnsdisco

    def _run(self):
        """run"""

        hosts = []
        for net in self.netlist:
            hosts += enumerate_network(net)
        current_app.logger.info(f'{self.__class__.__name__} enumerated {len(hosts)} hosts')
        self.stage_servicedisco.task(hosts)
        self.stage_sixdnsdisco.task(hosts)


@register_stage
class StorageSixEnum(Schedule):
    """enumerates v6 networks from storage data"""

    def __init__(self, schedule, stage_sixenumdisco):
        super().__init__(schedule)
        self.stage_sixenumdisco = stage_sixenumdisco

    def _run(self):
        """run"""

        targets = project_six_enums(StorageManager.get_all_six_address())
        current_app.logger.info(f'{self.__class__.__name__} projected {len(targets)} targets')
        self.stage_sixenumdisco.task(targets)


@register_stage
class StorageRescan(Schedule):
    """storage rescan"""

    def __init__(self, schedule, host_interval, service_interval, stage_servicedisco, stage_servicescan):  # pylint: disable=too-many-arguments
        super().__init__(schedule)
        self.host_interval = host_interval
        self.service_interval = service_interval
        self.stage_servicedisco = stage_servicedisco
        self.stage_servicescan = stage_servicescan

    def _run(self):
        """run"""

        hosts = StorageManager.get_rescan_hosts(self.host_interval)
        services = StorageManager.get_rescan_services(self.service_interval)
        current_app.logger.info(f'{self.__class__.__name__} rescaning {len(hosts)} hosts {len(services)} services')
        self.stage_servicedisco.task(hosts)
        self.stage_servicescan.task(services)


@register_stage
class SixDisco(QueueHandler):
    """cleanup list host ipv6 hosts (drop any outside scope) and pass it to service discovery"""

    def __init__(self, queues, stage_servicedisco, filter_nets=None):
        super().__init__(queues)
        self.filter_nets = filter_nets
        self.stage_servicedisco = stage_servicedisco

    def run(self):
        """run"""

        for pidb in self._drain():
            hosts = project_hosts(pidb)
            if self.filter_nets:
                hosts = filter_external_hosts(hosts, self.filter_nets)
            current_app.logger.info(f'{self.__class__.__name__} projected {len(hosts)} hosts')
            self.stage_servicedisco.task(hosts)


@register_stage
class ServiceDisco(QueueHandler):
    """do service discovery on targets"""

    def __init__(self, queues, stage_servicescan):
        super().__init__(queues)
        self.stage_servicescan = stage_servicescan

    def run(self):
        """run"""

        for pidb in self._drain():
            tmpdb = filter_tarpits(pidb)
            # list() should provide copy for list-in-loop pruning
            for service in list(tmpdb.services):
                if not service.state.startswith('open:'):
                    tmpdb.services.remove(service)
            services = project_services(tmpdb)
            current_app.logger.info(f'{self.__class__.__name__} projected {len(services)} services')
            self.stage_servicescan.task(services)


@register_stage
class StorageLoader(QueueHandler):
    """load queues to storage"""

    def __init__(self, queues, stage_storageimport):
        super().__init__(queues)
        self.stage_storageimport = stage_storageimport

    def run(self):
        """run"""

        for pidb in self._drain():
            current_app.logger.info(
                f'{self.__class__.__name__} loading {len(pidb.hosts)} '
                f'hosts {len(pidb.services)} services {len(pidb.vulns)} vulns {len(pidb.notes)} notes'
            )
            self.stage_storageimport.task(pidb)
