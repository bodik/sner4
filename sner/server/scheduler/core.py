# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler shared functions
"""

import csv
import json
import re
from abc import ABC, abstractmethod
from collections import namedtuple
from datetime import datetime
from io import StringIO
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from pathlib import Path
from random import random
from shutil import copy2
from uuid import uuid4

import psycopg2
import yaml
from flask import current_app
from sqlalchemy import cast, delete, distinct, func, select
from sqlalchemy.dialects.postgresql import ARRAY as pg_ARRAY, insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from sner.agent.modules import SERVICE_TARGET_REGEXP
from sner.server.extensions import db
from sner.server.parser import REGISTERED_PARSERS
from sner.server.scheduler.models import Excl, ExclFamily, Heatmap, Job, Queue, Readynet, Target
from sner.server.utils import windowed_query


SCHEDULER_LOCK_NUMBER = 1


def enumerate_network(arg):
    """enumerate ip address range"""

    network = ip_network(arg, strict=False)
    data = list(map(str, network.hosts()))

    # input is single address
    if network.prefixlen == network.max_prefixlen:
        data.insert(0, str(network.network_address))

    # add network/bcast addresses to range if it's not point-to-point link
    if network.prefixlen < (network.max_prefixlen-1):
        data.insert(0, str(network.network_address))
        if network.version == 4:
            data.append(str(network.broadcast_address))

    return data


def filter_already_queued(queue, targets):
    """filters already queued targets"""

    # TODO: revisit need for filtering, on_conflict_do_nothing might work better
    current_targets = {x[0]: 0 for x in windowed_query(db.session.query(Target.target).filter(Target.queue == queue), Target.id)}
    targets = [tgt for tgt in targets if tgt not in current_targets]
    return targets


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

    def __init__(self):
        self.excls = []
        for excl in Excl.query.all():
            self.excls.append(ExclMatcher.MATCHERS[excl.family](excl.value))

    def match(self, value):
        """match value against all exclusions/matchers"""

        for excl in self.excls:
            if excl.match(value):
                return True
        return False


class ExclMatcherImplInterface(ABC):  # pylint: disable=too-few-public-methods
    """base interface which must  be implemented by all available matchers"""

    @abstractmethod
    def __init__(self, match_to):
        """constructor"""

    @abstractmethod
    def match(self, value):
        """returns bool if value matches the initialized match_to"""


@ExclMatcher.register(ExclFamily.NETWORK)  # pylint: disable=too-few-public-methods
class ExclNetworkMatcher(ExclMatcherImplInterface):
    """network matcher"""

    def __init__(self, match_to):  # pylint: disable=super-init-not-called
        self.match_to = ip_network(match_to)

    def match(self, value):
        try:
            return ip_address(value) in self.match_to
        except ValueError:
            pass

        try:
            mtmp = re.match(SERVICE_TARGET_REGEXP, value)
            if mtmp:
                return ip_address(mtmp.group('host').replace('[', '').replace(']', '')) in self.match_to
        except ValueError:
            pass

        return False


@ExclMatcher.register(ExclFamily.REGEX)  # pylint: disable=too-few-public-methods
class ExclRegexMatcher(ExclMatcherImplInterface):
    """regex matcher"""

    def __init__(self, match_to):  # pylint: disable=super-init-not-called
        self.match_to = re.compile(match_to)

    def match(self, value):
        return bool(self.match_to.search(value))


class ExclImportException(Exception):
    """exclusion import error"""


class ExclManager:
    """exclustion manager"""

    EXPORT_FIELDNAMES = ['family', 'value', 'comment']

    @classmethod
    def import_data(cls, data, replace):
        """import from excl export csv"""
        try:
            imported = []
            for row in csv.DictReader(StringIO(data), cls.EXPORT_FIELDNAMES, quoting=csv.QUOTE_MINIMAL):
                imported.append(Excl(family=ExclFamily(row['family']), value=row['value'], comment=row['comment']))

            if imported:
                if replace:
                    db.session.query(Excl).delete()
                db.session.add_all(imported)
                db.session.commit()
        except (csv.Error, ValueError, SQLAlchemyError, psycopg2.Error) as exc:
            db.session.rollback()
            current_app.logger.exception(exc)
            raise ExclImportException() from None

    @classmethod
    def export(cls):
        """export excls to csv"""

        output_buffer = StringIO()
        output = csv.DictWriter(output_buffer, cls.EXPORT_FIELDNAMES, restval='', quoting=csv.QUOTE_ALL)
        for row in db.session.query(Excl.family, Excl.value, Excl.comment).all():
            output.writerow(row._asdict())

        return output_buffer.getvalue()


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

            db.session.execute(pg_insert(Target.__table__), enqueued)
            hot_hashvals = set(SchedulerService.grep_hot_hashvals(enqueued_hashvals))
            for thashval in (enqueued_hashvals - hot_hashvals):
                db.session.execute(
                    pg_insert(Readynet)
                    .values(queue_id=queue.id, hashval=thashval)
                    .on_conflict_do_nothing(index_elements=[Readynet.queue_id, Readynet.hashval])
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

        qpath = Path(queue.data_abspath)
        if qpath.exists():
            qpath.rmdir()

        SchedulerService.get_lock()
        db.session.delete(queue)
        db.session.commit()
        SchedulerService.release_lock()


class JobManager:
    """job governance"""

    # TODO: naming here ?????
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

        heat_count = db.session.execute(
            pg_insert(Heatmap.__table__)
            .values(hashval=hashval, count=1)
            .on_conflict_do_update(index_elements=['hashval'], set_=dict(count=Heatmap.count+1))
            .returning(Heatmap.count)
        ).scalar()

        if current_app.config['SNER_HEATMAP_HOT_LEVEL'] and (heat_count >= current_app.config['SNER_HEATMAP_HOT_LEVEL']):
            db.session.execute(delete(Readynet.__table__).filter(Readynet.hashval == hashval))

        db.session.commit()
        return heat_count

    @classmethod
    def heatmap_pop(cls, hashval):
        """account value (decrement counter) in heatmap and update readynets"""

        heat_count = db.session.execute(
            pg_insert(Heatmap.__table__)
            .values(hashval=hashval, count=1)
            .on_conflict_do_update(index_elements=['hashval'], set_=dict(count=Heatmap.count-1))
            .returning(Heatmap.count)
        ).scalar()

        if random() < cls.HEATMAP_GC_PROBABILITY:
            db.session.execute(delete(Heatmap.__table__).filter(Heatmap.count == 0))

        if current_app.config['SNER_HEATMAP_HOT_LEVEL'] and (heat_count+1 == current_app.config['SNER_HEATMAP_HOT_LEVEL']):
            for queue_id in db.session.execute(select(func.distinct(Target.queue_id)).filter(Target.hashval == hashval)).scalars().all():
                db.session.execute(pg_insert(Readynet.__table__).values(queue_id=queue_id, hashval=hashval))

        db.session.commit()
        return heat_count

    @staticmethod
    def grep_hot_hashvals(hashvals):
        """get hot hashvals among argument list"""

        if not current_app.config['SNER_HEATMAP_HOT_LEVEL']:
            return []

        return db.session.execute(
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

        readynet_hashval = db.session.execute(
            select(Readynet.hashval).filter(Readynet.queue_id == queue.id).order_by(func.random()).limit(1)
        ).scalar()
        if not readynet_hashval:
            return None

        target_id, target = db.session.execute(
            select(Target.id, Target.target)
            .filter(Target.queue_id == queue.id, Target.hashval == readynet_hashval)
            .order_by(func.random())
            .limit(1)
        ).first()

        db.session.execute(delete(Target.__table__).filter(Target.id == target_id))
        # prune readynet if no targets left for current queue
        db.session.execute(
            delete(Readynet.__table__)
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
        blacklist = ExclMatcher()

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
