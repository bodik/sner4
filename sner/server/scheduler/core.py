# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler shared functions
"""

import json
import re
from abc import ABC, abstractmethod
from collections import defaultdict, namedtuple
from datetime import datetime
from enum import Enum
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from pathlib import Path
from random import random
from shutil import copy2
from uuid import uuid4

import yaml
from flask import current_app
from sqlalchemy import cast, delete, distinct, func, select
from sqlalchemy.dialects.postgresql import ARRAY as pg_ARRAY, insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from sner.agent.modules import SERVICE_TARGET_REGEXP
from sner.plugin.six_enum_discover.agent import SIXENUM_TARGET_REGEXP
from sner.server.extensions import db
from sner.server.parser import REGISTERED_PARSERS
from sner.server.scheduler.models import Heatmap, Job, Queue, Readynet, Target


SCHEDULER_LOCK_NUMBER = 1


def enumerate_network(arg):
    """enumerate ip address range"""

    network = ip_network(arg, strict=False)

    # input is single address
    if network.prefixlen == network.max_prefixlen:
        return [str(network.network_address)]

    # enumerate hosts
    data = list(map(str, network.hosts()))

    # add network/bcast addresses to range if it's not point-to-point link
    if network.prefixlen < (network.max_prefixlen-1):
        data.insert(0, str(network.network_address))
        if network.version == 4:
            data.append(str(network.broadcast_address))

    return data


def sixenum_target_boundaries(value):
    """returns tuple(first, last)"""

    if not (mtmp := re.match(SIXENUM_TARGET_REGEXP, value)):
        raise ValueError('not valid sixenum target')

    addr = mtmp.group('scan6dst')

    if '-' in addr:
        first, last = addr.split('-')
        tmp = first.split(':')
        tmp[-1] = last
        last = ':'.join(tmp)
        return first, last

    return addr, addr


class ExclFamily(Enum):
    """exclusion family enum"""

    NETWORK = 'network'
    REGEX = 'regex'


class ExclMatcher():
    """object matching value againts set of exclusions/rules"""

    MATCHERS = {}

    @staticmethod
    def register(family):
        """register matcher class to the excl.family"""

        def register_real(cls):
            if cls not in ExclMatcher.MATCHERS:
                ExclMatcher.MATCHERS[family] = cls
            return cls
        return register_real

    def __init__(self, config):
        self.excls = [
            ExclMatcher.MATCHERS[ExclFamily(family)](value)
            for family, value in config
        ]

    def match(self, value):
        """match value against all exclusions/matchers"""

        for excl in self.excls:
            if excl.match(value):
                return True
        return False


class ExclMatcherImplBase(ABC):  # pylint: disable=too-few-public-methods
    """base interface which must  be implemented by all available matchers"""

    def __init__(self, match_to):
        self.match_to = self._initialize(match_to)

    @abstractmethod
    def _initialize(self, match_to):
        """initialize matcher impl"""

    @abstractmethod
    def match(self, value):
        """returns bool if value matches the initialized match_to"""

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.match_to}>'


@ExclMatcher.register(ExclFamily.NETWORK)
class NetworkExclMatcher(ExclMatcherImplBase):  # pylint: disable=too-few-public-methods
    """network matcher"""

    def _initialize(self, match_to):
        return ip_network(match_to)

    def _test_addr(self, value):
        try:
            return ip_address(value) in self.match_to
        except ValueError:
            return False

    def match(self, value):
        # test value as plain address
        if self._test_addr(value):
            return True

        # test value as service target
        if mtmp := re.match(SERVICE_TARGET_REGEXP, value):
            return self._test_addr(mtmp.group('host').replace('[', '').replace(']', ''))

        # test value as sixenum target
        if mtmp := re.match(SIXENUM_TARGET_REGEXP, value):
            first, last = map(ip_address, sixenum_target_boundaries(value))

            # first or last enum addr is in excluded range
            if self._test_addr(first) or self._test_addr(last):
                return True

            # excluded range could be smaller than enum, check if excluded range does not belong into enum itself
            if (
                (first.version == self.match_to.version)
                and ((first <= self.match_to.network_address <= last) or (first <= self.match_to.broadcast_address <= last))
            ):
                return True

        return False


@ExclMatcher.register(ExclFamily.REGEX)
class RegexExclMatcher(ExclMatcherImplBase):  # pylint: disable=too-few-public-methods
    """regex matcher"""

    def _initialize(self, match_to):
        return re.compile(match_to)

    def match(self, value):
        return bool(self.match_to.search(value))


class QueueManager:
    """Governs queues, readynets and targets"""

    @staticmethod
    def enqueue(queue, targets):
        """enqueue targets to queue"""

        enqueued = []
        enqueued_hashvals = set()

        for target in filter(None, map(lambda x: x.strip(), targets)):
            thashval = SchedulerService.hashval(target)
            enqueued.append({'queue_id': queue.id, 'target': target, 'hashval': thashval})
            enqueued_hashvals.add(thashval)

        if enqueued:
            SchedulerService.get_lock()

            conn = db.session.connection()
            conn.execute(pg_insert(Target), enqueued)
            hot_hashvals = set(SchedulerService.grep_hot_hashvals(enqueued_hashvals))
            for thashval in (enqueued_hashvals - hot_hashvals):
                conn.execute(
                    pg_insert(Readynet)
                    .values(queue_id=queue.id, hashval=thashval)
                    .on_conflict_do_nothing(constraint='readynet_pkey')
                )
            db.session.commit()

            SchedulerService.release_lock()

    @staticmethod
    def flush(queue):
        """queue flush; flush all targets from queue"""

        SchedulerService.get_lock()

        Target.query.filter(Target.queue_id == queue.id).delete()
        Readynet.query.filter(Readynet.queue_id == queue.id).delete()
        db.session.commit()

        SchedulerService.release_lock()

    @staticmethod
    def prune(queue):
        """queue prune; delete all queue jobs"""

        for job in queue.jobs:
            JobManager.delete(job)

    @staticmethod
    def delete(queue):
        """queue delete; delete all jobs in cascade (deals with output files)"""

        for job in queue.jobs:
            JobManager.delete(job)

        try:
            qpath = Path(queue.data_abspath)
            if qpath.exists():
                qpath.rmdir()
        except OSError as exc:  # pragma: no cover  ; wont test
            raise RuntimeError(f'failed to remove queue directory: {exc.strerror}') from None

        SchedulerService.get_lock()
        db.session.delete(queue)
        db.session.commit()
        SchedulerService.release_lock()


class JobManager:
    """job governance"""

    @staticmethod
    def create(queue, assigned_targets):
        """
        create job for queue with targets

        :return: agent assignment data
        :rtype: dict
        """

        assignment = {
            'id': str(uuid4()),
            'config': {} if queue.config is None else yaml.safe_load(queue.config),
            'targets': assigned_targets
        }
        db.session.add(Job(id=assignment['id'], queue=queue, assignment=json.dumps(assignment)))
        db.session.commit()
        return assignment

    @staticmethod
    def finish(job, retval, output):
        """writeback job results"""

        opath = Path(job.output_abspath)
        opath.parent.mkdir(parents=True, exist_ok=True)
        opath.write_bytes(output)
        job.retval = retval
        job.time_end = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def reconcile(job):
        """
        job reconcile. broken agent might generate orphaned jobs with targets accounted in heatmap.
        reconcile job forces to fail selected job and reclaim it's heatmap counts.
        """

        if job.retval is not None:
            current_app.logger.error('cannot reconcile completed job %s', job.id)
            raise RuntimeError('cannot reconcile completed job')

        SchedulerService.get_lock()

        job.retval = -1
        for target in json.loads(job.assignment)['targets']:
            SchedulerService.heatmap_pop(SchedulerService.hashval(target))

        SchedulerService.release_lock()

    @staticmethod
    def repeat(job):
        """job repeat; reschedule targets"""

        QueueManager.enqueue(job.queue, json.loads(job.assignment)['targets'])

    @staticmethod
    def parse(job):
        """parse job and return data"""

        module = yaml.safe_load(job.queue.config)['module']
        parser_impl = REGISTERED_PARSERS[module]
        return parser_impl.parse_path(job.output_abspath)

    @staticmethod
    def archive(job):
        """job archive"""

        current_app.logger.info(f'archive_job {job.id} ({job.queue.name})')
        archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
        archive_dir.mkdir(parents=True, exist_ok=True)
        copy2(job.output_abspath, archive_dir)

    @staticmethod
    def delete(job):
        """job delete"""

        # deleting running job would corrupt heatmap
        if job.retval is None:
            current_app.logger.error('cannot delete running job %s', job.id)
            raise RuntimeError('cannot delete running job')

        opath = Path(job.output_abspath)
        if opath.exists():
            opath.unlink()
        db.session.delete(job)
        db.session.commit()


RandomTarget = namedtuple('RandomTarget', ['id', 'target', 'hashval'])


class SchedulerServiceBusyException(Exception):
    """raised when timeout is reached when obtaining scheduling service lock"""


class SchedulerService:
    """
    rate-limiting scheduling service (nacelnik.mk1 design)

    Naive implementation (queues/targets, heatmap) for rate-limiting but rantom
    target selection does not perform well with large queue sizes. Either would
    require to pass full heatmap processing for each target (ends up creating
    large temporary tables) or requires re-iterating of all targets in
    worst-case.

    Nacelnik.Mk1 (apadrta@cesnet.cz) proposes maintaining datastructure
    (queues/targets, readynet, heatmap) which optimizes target selection
    via readynet pre-computed maps.
    """

    TIMEOUT_JOB_ASSIGN = 3
    TIMEOUT_JOB_OUTPUT = 30
    HEATMAP_GC_PROBABILITY = 0.1

    @staticmethod
    def get_lock(timeout=0):
        """wait for database lock or raise exception"""

        try:
            db.session.execute(
                'SET LOCAL lock_timeout=:timeout; SELECT pg_advisory_lock(:locknum);',
                {'timeout': timeout*100, 'locknum': SCHEDULER_LOCK_NUMBER}
            )
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.warning('failed to acquire SchedulerService lock')
            raise SchedulerServiceBusyException() from None

    @staticmethod
    def release_lock():
        """release scheduling lock"""

        db.session.execute('SELECT pg_advisory_unlock(:locknum);', {'locknum': SCHEDULER_LOCK_NUMBER})

    @staticmethod
    def hashval(value):
        """computes rate-limit heatmap hash value"""

        if mtmp := re.match(SERVICE_TARGET_REGEXP, value):
            value = mtmp.group('host')
            if (value[0] == '[') and (value[-1] == ']'):
                value = value[1:-1]

        if mtmp := re.match(SIXENUM_TARGET_REGEXP, value):
            value = mtmp.group('scan6dst').split('-')[0]

        try:
            addr = ip_address(value)
            if isinstance(addr, IPv4Address):
                return str(ip_network(f'{ip_address(value)}/24', strict=False))
            if isinstance(addr, IPv6Address):
                return str(ip_network(f'{ip_address(value)}/48', strict=False))
        except ValueError:
            pass

        return value

    @staticmethod
    def heatmap_put(hashval):
        """account value (increment counter) in heatmap and update readynets"""

        conn = db.session.connection()
        heat_count = conn.execute(
            pg_insert(Heatmap)
            .values(hashval=hashval, count=1)
            .on_conflict_do_update(constraint='heatmap_pkey', set_={"count": Heatmap.count + 1})
            .returning(Heatmap.count)
        ).scalar()

        if current_app.config['SNER_HEATMAP_HOT_LEVEL'] and (heat_count >= current_app.config['SNER_HEATMAP_HOT_LEVEL']):
            conn.execute(delete(Readynet).filter(Readynet.hashval == hashval))

        db.session.commit()
        return heat_count

    @classmethod
    def heatmap_pop(cls, hashval):
        """account value (decrement counter) in heatmap and update readynets"""

        conn = db.session.connection()
        heat_count = conn.execute(
            pg_insert(Heatmap)
            .values(hashval=hashval, count=1)
            .on_conflict_do_update(constraint='heatmap_pkey', set_={"count": Heatmap.count - 1})
            .returning(Heatmap.count)
        ).scalar()

        if random() < cls.HEATMAP_GC_PROBABILITY:
            conn.execute(delete(Heatmap).filter(Heatmap.count == 0))

        if current_app.config['SNER_HEATMAP_HOT_LEVEL'] and (heat_count+1 == current_app.config['SNER_HEATMAP_HOT_LEVEL']):
            for queue_id in db.session.execute(select(func.distinct(Target.queue_id)).filter(Target.hashval == hashval)).scalars().all():
                conn.execute(pg_insert(Readynet).values(queue_id=queue_id, hashval=hashval))

        db.session.commit()
        return heat_count

    @staticmethod
    def grep_hot_hashvals(hashvals):
        """get hot hashvals among argument list"""

        if not current_app.config['SNER_HEATMAP_HOT_LEVEL']:
            return []

        return db.session.connection().execute(
            select(Heatmap.hashval)
            .filter(
                Heatmap.hashval.in_(hashvals),
                Heatmap.count >= current_app.config['SNER_HEATMAP_HOT_LEVEL']
            )
        ).scalars().all()

    @staticmethod
    def _get_assignment_queue(queue_name, client_caps):
        """
        select queue for target assignment accounting client request constraints

        * queue must be active
        * client capabilities (caps) must conform queue requirements (reqs)
        * queue must have any rate-limit available targets/networks enqueued
        * must suffice client requested parameters (name)
        * queue is selected with priority in respect, but at random on same prio levels

        :return: selected queue
        :rtype: sner.server.scheduler.model.Queue
        """

        query = select(Queue).filter(
            Queue.active,
            Queue.reqs.contained_by(cast(client_caps, pg_ARRAY(db.String))),
            Queue.id.in_(select(distinct(Readynet.queue_id)))
        )
        if queue_name:
            query = query.filter(Queue.name == queue_name)
        query = query.order_by(Queue.priority.desc(), func.random())
        return db.session.execute(query).scalars().first()

    @staticmethod
    def _pop_random_target(queue):
        """
        pop random target from queue and update readynet info

        :return: random target properties as tuple
        :rtype: sner.server.scheduler.core.RandomTarget
        """

        conn = db.session.connection()

        readynet_hashval = conn.execute(
            select(Readynet.hashval).filter(Readynet.queue_id == queue.id).order_by(func.random()).limit(1)
        ).scalar()
        if not readynet_hashval:
            return None

        target_id, target = conn.execute(
            select(Target.id, Target.target)
            .filter(Target.queue_id == queue.id, Target.hashval == readynet_hashval)
            .order_by(func.random())
            .limit(1)
        ).first()

        conn.execute(delete(Target).filter(Target.id == target_id))
        # prune readynet if no targets left for current queue
        conn.execute(
            delete(Readynet)
            .filter(
                Readynet.queue_id == queue.id,
                Readynet.hashval == readynet_hashval,
                select(func.count(Target.id)).filter(Target.queue_id == queue.id, Target.hashval == readynet_hashval).scalar_subquery() == 0
            )
        )

        db.session.commit()
        return RandomTarget(target_id, target, readynet_hashval)

    @classmethod
    def job_assign(cls, queue_name, client_caps):
        """
        assign job for agent

        * select suitable queue
        * pop random target
            * select random readynet for queue (readynets reflects current rate-limit heatmap state)
            * pop random target within selected readynet
            * cleanup readynet if queue does not hold any target in same readynet
        * update rate-limit heatmap
            * deactivate readynet for all queues if it becomes hot
        """

        cls.get_lock(cls.TIMEOUT_JOB_ASSIGN)

        assignment = {}  # nowork
        assigned_targets = []
        blacklist = ExclMatcher(current_app.config['SNER_EXCLUSIONS'])

        queue = cls._get_assignment_queue(queue_name, client_caps)
        if not queue:
            SchedulerService.release_lock()
            return assignment

        while len(assigned_targets) < queue.group_size:
            rtarget = cls._pop_random_target(queue)
            if not rtarget:
                break
            if blacklist.match(rtarget.target):
                continue
            assigned_targets.append(rtarget.target)
            cls.heatmap_put(rtarget.hashval)

        if assigned_targets:
            assignment = JobManager.create(queue, assigned_targets)

        cls.release_lock()
        return assignment

    @classmethod
    def job_output(cls, job, retval, output):
        """
        receive output from assigned job

        * for each target update rate-limit heatmap
            * if readynet of the target becomes cool activate it for all queues
        """

        cls.get_lock(cls.TIMEOUT_JOB_OUTPUT)

        JobManager.finish(job, retval, output)
        for target in json.loads(job.assignment)['targets']:
            cls.heatmap_pop(cls.hashval(target))

        cls.release_lock()

    @classmethod
    def readynet_recount(cls):
        """
        rescan targets and update readynets table for new heatmap hot level
        """

        cls.get_lock()
        conn = db.session.connection()

        if current_app.config['SNER_HEATMAP_HOT_LEVEL']:
            hot_hashvals = set(conn.execute(
                select(Heatmap.hashval).filter(Heatmap.count >= current_app.config['SNER_HEATMAP_HOT_LEVEL'])
            ).scalars().all())

            # all heatmap hashvals over limit remove from readynet
            conn.execute(delete(Readynet).filter(Readynet.hashval.in_(hot_hashvals)))
        else:
            hot_hashvals = set()

        # for all target hashvals except over limit insert as readynet for all queues
        all_hashvals = set(conn.execute(select(func.distinct(Target.hashval))).scalars().all())
        for thashval in (all_hashvals - hot_hashvals):
            for queue_id in conn.execute(select(func.distinct(Target.queue_id)).filter(Target.hashval == thashval)).scalars().all():
                conn.execute(
                    pg_insert(Readynet)
                    .values(queue_id=queue_id, hashval=thashval)
                    .on_conflict_do_nothing(constraint='readynet_pkey')
                )

        db.session.commit()
        cls.release_lock()

    @classmethod
    def heatmap_check(cls):
        """
        check if heatmap corresponds with assigned targets from running jobs

        :return: True if the database is in an okay state, False otherwise.
        :rtype: bool
        """

        cls.get_lock()

        ref_heatmap = defaultdict(int)
        for job in Job.query.filter(Job.retval == None).all():  # noqa: E711  pylint: disable=singleton-comparison
            for target in json.loads(job.assignment)['targets']:
                ref_heatmap[SchedulerService.hashval(target)] += 1

        db_heatmap = {
            item.hashval: item.count
            for item in Heatmap.query.all()
            if item.count != 0
        }

        keys_only_in_dict1 = set(ref_heatmap.keys()) - set(db_heatmap.keys())
        keys_only_in_dict2 = set(db_heatmap.keys()) - set(ref_heatmap.keys())
        different_values = {
            key: (ref_heatmap[key], db_heatmap[key])
            for key in ref_heatmap
            if (key in db_heatmap) and (ref_heatmap[key] != db_heatmap[key])
        }

        heatmaps_equal = not bool(keys_only_in_dict1 or keys_only_in_dict2 or different_values)
        cls.release_lock()
        return heatmaps_equal
