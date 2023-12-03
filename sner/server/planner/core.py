# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core
"""

import logging
import subprocess
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from fcntl import flock, LOCK_EX, LOCK_NB, LOCK_UN
from ipaddress import ip_address, ip_network, IPv6Address
from pathlib import Path
from time import sleep, time

import psycopg2
from flask import current_app
from pytimeparse import parse as timeparse
from sqlalchemy import select
from sqlalchemy.orm.exc import NoResultFound

from sner.lib import format_host_address, get_nested_key, TerminateContextMixin
from sner.server.extensions import db
from sner.server.scheduler.core import enumerate_network, JobManager, QueueManager
from sner.server.scheduler.models import Queue, Job, Target
from sner.server.storage.core import StorageManager
from sner.server.storage.versioninfo import VersioninfoManager


def configure_logging():
    """configure server/app logging"""

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'formatter_planner': {
                'format': 'sner.planner [%(asctime)s] %(levelname)s %(message)s',
                'datefmt': '%d/%b/%Y:%H:%M:%S %z'
            }
        },
        'handlers': {
            'console_planner': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'formatter_planner'
            }
        },
        'loggers': {
            'sner.server': {
                'level': 'INFO',
                'handlers': ['console_planner']
            }
        }
    })


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


def project_sixenum_targets(hosts):
    """project targets for six_enum_discover agent from list of ipv6 addresses"""

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

        targets.add(f'sixenum://{target}')

    return list(targets)


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


def filter_external_hosts(hosts, nets):
    """filter addrs not belonging to nets list"""

    whitelist = [ip_network(net) for net in nets]
    return [item for item in hosts if any(ip_address(item) in net for net in whitelist)]


def filter_service_open(pidb):
    """filter open services"""

    # list() should provide copy for list-in-loop pruning
    for service in list(pidb.services):
        if not service.state.startswith('open:'):
            pidb.services.remove(service)
    return pidb


class Stage(ABC):  # pylint: disable=too-few-public-methods
    """planner stage base"""

    @abstractmethod
    def run(self):
        """stage main runnable"""


class Schedule(Stage):  # pylint: disable=too-few-public-methods
    """schedule base"""

    def __init__(self, schedule):
        self.schedule = schedule
        self.lastrun_path = Path(f'{current_app.config["SNER_VAR"]}/lastrun.{self.__class__.__name__}')

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


class QueueHandler(Stage):  # pylint: disable=too-few-public-methods
    """queue handler base"""

    def __init__(self, queue_name):
        try:
            self.queue = Queue.query.filter(Queue.name == queue_name).one()
        except NoResultFound:
            raise ValueError(f'missing queue "{queue_name}"') from None

    def _drain(self):
        """drain queue and yield PIDBs"""

        for aajob in Job.query.filter(Job.queue_id == self.queue.id, Job.retval == 0).all():
            current_app.logger.info(f'{self.__class__.__name__} drain {aajob.id} ({aajob.queue.name})')
            try:
                parsed = JobManager.parse(aajob)
            except Exception as exc:  # pylint: disable=broad-except
                current_app.logger.error(f'{self.__class__.__name__} failed to drain {aajob.id} ({aajob.queue.name}), {exc}', exc_info=True)
                aajob.retval += 1000
                db.session.commit()
                continue
            yield parsed
            JobManager.archive(aajob)
            JobManager.delete(aajob)

    def task(self, data):
        """enqueue data/targets into all configured queues"""

        already_queued = db.session.connection().execute(select(Target.target).filter(Target.queue == self.queue)).scalars().all()
        enqueue = list(set(data) - set(already_queued))
        QueueManager.enqueue(self.queue, enqueue)
        current_app.logger.info(f'{self.__class__.__name__} enqueued {len(enqueue)} targets to "{self.queue.name}"')


class DummyStage(Stage):  # pylint: disable=too-few-public-methods
    """dummy testing stage"""

    def __init__(self):
        self.task_count = 0
        self.task_args = None
        self.run_count = 0
        self.run_args = None

    def task(self, data):
        """dummy"""

        self.task_count += 1
        self.task_args = data

    def run(self):
        """dummy impl"""


class NetlistEnum(Schedule):  # pylint: disable=too-few-public-methods
    """periodic host discovery via list of ipv4 networks"""

    def __init__(self, schedule, netlist, next_stages):
        super().__init__(schedule)
        self.netlist = netlist
        self.next_stages = next_stages

    def _run(self):
        """run"""

        hosts = []
        for net in self.netlist:
            hosts += enumerate_network(net)
        current_app.logger.info(f'{self.__class__.__name__} enumerated {len(hosts)} hosts')
        for stage in self.next_stages:
            stage.task(hosts)


class StorageSixEnum(Schedule):  # pylint: disable=too-few-public-methods
    """enumerates v6 networks from storage data"""

    def __init__(self, schedule, next_stage):
        super().__init__(schedule)
        self.next_stage = next_stage

    def _run(self):
        """run"""

        targets = project_sixenum_targets(StorageManager.get_all_six_address())
        current_app.logger.info(f'{self.__class__.__name__} projected {len(targets)} targets')
        self.next_stage.task(targets)


class StorageRescan(Schedule):  # pylint: disable=too-few-public-methods
    """storage rescan"""

    def __init__(self, schedule, host_interval, servicedisco_stage, service_interval, servicescan_stages):  # pylint: disable=too-many-arguments
        super().__init__(schedule)
        self.host_interval = host_interval
        self.servicedisco_stage = servicedisco_stage
        self.service_interval = service_interval
        self.servicescan_stages = servicescan_stages

    def _run(self):
        """run"""

        hosts = StorageManager.get_rescan_hosts(self.host_interval)
        services = StorageManager.get_rescan_services(self.service_interval)
        current_app.logger.info(f'{self.__class__.__name__} rescaning {len(hosts)} hosts {len(services)} services')
        self.servicedisco_stage.task(hosts)
        for stage in self.servicescan_stages:
            stage.task(services)


class SixDisco(QueueHandler):
    """cleanup list host ipv6 hosts (drop any outside scope) and pass it to service discovery"""

    def __init__(self, queue_name, next_stage, filternets=None):
        super().__init__(queue_name)
        self.next_stage = next_stage
        self.filternets = filternets

    def run(self):
        """run"""

        for pidb in self._drain():
            hosts = project_hosts(pidb)
            if self.filternets:
                hosts = filter_external_hosts(hosts, self.filternets)
            current_app.logger.info(f'{self.__class__.__name__} projected {len(hosts)} hosts')
            self.next_stage.task(hosts)


class ServiceDisco(QueueHandler):
    """do service discovery on targets"""

    def __init__(self, queue_name, next_stages):
        super().__init__(queue_name)
        self.next_stages = next_stages

    def run(self):
        """run"""

        for pidb in self._drain():
            tmpdb = filter_tarpits(pidb)
            tmpdb = filter_service_open(tmpdb)
            services = project_services(tmpdb)
            current_app.logger.info(f'{self.__class__.__name__} projected {len(services)} services')
            for stage in self.next_stages:
                stage.task(services)


class StorageLoader(QueueHandler):
    """load queues to storage"""

    def run(self):
        """run"""

        for pidb in self._drain():
            current_app.logger.info(
                f'{self.__class__.__name__} loading {len(pidb.hosts)} '
                f'hosts {len(pidb.services)} services {len(pidb.vulns)} vulns {len(pidb.notes)} notes'
            )
            StorageManager.import_parsed(pidb)


class StorageCleanup(Stage):  # pylint: disable=too-few-public-methods
    """cleanup storage"""

    def run(self):
        """cleanup storage"""

        StorageManager.cleanup_storage()
        current_app.logger.debug(f'{self.__class__.__name__} finished')


class RebuildVersioninfoMap(Schedule):  # pylint: disable=too-few-public-methods
    """recount versioninfo map"""

    def _run(self):
        """run"""

        VersioninfoManager.rebuild()
        current_app.logger.info(f'{self.__class__.__name__} finished')


class StorageRebuilderFileLock:
    """non-blocking file-based lock"""

    def __init__(self):
        self.lock_path = f"{current_app.config['SNER_VAR']}/{self.__class__.__name__}.lock"
        self.lock = None

    def acquire(self):
        """lock"""

        self.lock = Path(self.lock_path).open(mode="w+", encoding="utf-8")  # pylint: disable=consider-using-with
        try:
            flock(self.lock, LOCK_EX | LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            self.lock = None
            return False

        return True

    def release(self):
        """unlock"""

        flock(self.lock, LOCK_UN)
        self.lock.close()
        self.lock = None


@dataclass
class StorageRebuilderCrontabItem:
    fname: str
    period: int
    next_run: int


class StorageRebuilder(Stage):
    """runs rebuild tasks on background in detached processes"""

    def __init__(self, config):
        now = time()
        self.crontab = [StorageRebuilderCrontabItem(*item, now + item[1]) for item in config]
        self.lock = StorageRebuilderFileLock()

    def _next_to_run(self):

        if not self.lock.acquire():
            return None
        self.lock.release()

        now = time()
        for idx, item in enumerate(self.crontab):
            if now > item.next_run:
                run_item = self.crontab.pop(idx)
                self.crontab.append(StorageRebuilderCrontabItem(run_item.fname, run_item.period, now+run_item.period))
                return run_item
        return None

    def run(self):
        if run_item := self._next_to_run():
            current_app.logger.debug(f'{self.__class__.__name__} run {run_item}')
            subprocess.Popen(['/usr/bin/sleep', '5'], close_fds=True, start_new_session=True)
            #subprocess.Popen([sys.executable, sys.argv[0], run_item.fname], close_fds=True, start_new_session=True)


class Planner(TerminateContextMixin):
    """planner"""

    LOOPSLEEP = 1

    def __init__(self, config=None, oneshot=False):
        configure_logging()
        self.log = current_app.logger
        self.log.setLevel(logging.DEBUG if current_app.config['DEBUG'] else logging.INFO)

        self.original_signal_handlers = {}
        self.loop = None
        self.oneshot = oneshot
        self.config = config
        self.stages = {}

        if self.config:
            self._setup_stages()

    def _setup_stages(self):
        """setup plannet stages"""

        sscan_stages = []
        for sscan_qname in self.config['stage']['service_scan']['queues']:
            self.stages[sscan_qname] = StorageLoader(sscan_qname)
            sscan_stages.append(self.stages[sscan_qname])

        self.stages['service_disco'] = ServiceDisco(
            self.config['stage']['service_disco']['queue'],
            sscan_stages
        )

        self.stages['six_dns_disco'] = SixDisco(
            self.config['stage']['six_dns_disco']['queue'],
            self.stages['service_disco'],
            self.config['home_netranges_ipv6']
        )
        self.stages['six_enum_disco'] = SixDisco(
            self.config['stage']['six_enum_disco']['queue'],
            self.stages['service_disco']
        )

        self.stages['netlist_enum'] = NetlistEnum(
            self.config['stage']['netlist_enum']['schedule'],
            self.config['home_netranges_ipv4'],
            [self.stages['service_disco'], self.stages['six_dns_disco']]
        )

        self.stages['storage_six_enum'] = StorageSixEnum(
            self.config['stage']['storage_six_enum']['schedule'],
            self.stages['six_enum_disco']
        )
        self.stages['storage_rescan'] = StorageRescan(
            self.config['stage']['storage_rescan']['schedule'],
            self.config['stage']['storage_rescan']['host_interval'],
            self.stages['service_disco'],
            self.config['stage']['storage_rescan']['service_interval'],
            sscan_stages
        )

        if standalones := get_nested_key(self.config, 'stage', 'load_standalone', 'queues'):
            for qname in standalones:
                queue = Queue.query.filter_by(name=qname).one()
                self.stages[f'load_standalone-{queue.id}'] = StorageLoader(qname)

        self.stages['storage_cleanup'] = StorageCleanup()

#        if get_nested_key(self.config, 'stage', 'rebuild_versioninfo_map'):
#            self.stages['rebuild_versioninfo_map'] = RebuildVersioninfoMap(self.config['stage']['rebuild_versioninfo_map']['schedule'])

        self.stages['storage_rebuilder'] = StorageRebuilder([
            ('abc', 1),
            ('cde', 5),
        ])

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """terminate at once"""

        self.log.info('received terminate')
        self.loop = False

    def run(self):
        """run planner loop"""

        self.log.info(f'startup, {len(self.stages)} configured stages')
        self.loop = True

        with self.terminate_context():
            while self.loop:
                for name, stage in self.stages.items():
                    try:
                        current_app.logger.debug(f'stage run {name} {stage}')
                        stage.run()
                    except psycopg2.OperationalError as exc:  # pragma: no cover  ; won't test
                        current_app.logger.error(f'stage failed, {name} {stage}, {exc}', exc_info=True)
                        db.session.rollback()
                    except Exception as exc:  # pragma: no cover  ; pylint: disable=broad-except
                        current_app.logger.error(f'stage failed, {name} {stage}, {exc}', exc_info=True)

                if self.oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    # support for long loops, but allow fast shutdown
                    for _ in range(self.LOOPSLEEP):
                        if self.loop:
                            sleep(1)

        self.log.info('exit')
        return 0
