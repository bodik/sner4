# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler shared functions
"""

import base64
import binascii
import json
import os
from datetime import datetime
from http import HTTPStatus
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from random import random
from uuid import uuid4

import jsonschema
import yaml
from flask import current_app
from sqlalchemy import cast, delete, distinct, func, select
from sqlalchemy.dialects.postgresql import ARRAY as pg_ARRAY, insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

import sner.agent.protocol
from sner.server.extensions import db
from sner.server.scheduler.models import Heatmap, Job, Queue, Readynet, Target
from sner.server.utils import ExclMatcher, windowed_query


TIMEOUT_ASSIGN = 3
TIMEOUT_OUTPUT = 30
HEATMAP_GC_PROBABILITY = 0.1


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


def wait_for_lock(table_name, timeout):
    """wait for database lock. lock must be released by caller either by commit or rollback"""

    try:
        db.session.execute(f'SET LOCAL lock_timeout={timeout*1000}; LOCK TABLE {table_name}')
        return True
    except SQLAlchemyError:
        db.session.rollback()

    current_app.logger.warning('failed to acquire table lock')
    return False


def target_hashval(value):
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


def heatmap_put(value):
    """account value (increment counter) in heatmap and update readynets"""

    heatmap_hashval_count = db.session.execute(
        pg_insert(Heatmap.__table__)
        .values(hashval=value, count=1)
        .on_conflict_do_update(index_elements=['hashval'], set_=dict(count=Heatmap.count+1))
        .returning(Heatmap.count)
    ).scalar()
    if heatmap_hashval_count >= current_app.config['SNER_HEATMAP_HOT_LEVEL']:
        db.session.execute(delete(Readynet.__table__).filter(Readynet.hashval == value))


def heatmap_pop(value):
    """account value (decrement counter) in heatmap and update readynets"""

    heatmap_hashval_count = db.session.execute(
        pg_insert(Heatmap.__table__)
        .values(hashval=value, count=1)
        .on_conflict_do_update(index_elements=['hashval'], set_=dict(count=Heatmap.count-1))
        .returning(Heatmap.count)
    ).scalar()
    if heatmap_hashval_count+1 == current_app.config['SNER_HEATMAP_HOT_LEVEL']:
        for queue_id in db.session.execute(select(func.distinct(Target.queue_id)).filter(Target.hashval == value)).scalars().all():
            db.session.execute(pg_insert(Readynet.__table__).values(queue_id=queue_id, hashval=value))

    if random() < HEATMAP_GC_PROBABILITY:
        db.session.execute(delete(Heatmap.__table__).filter(Heatmap.count == 0))


def readynet_updates(queue, hashvals):
    """for given queue, enable all non-hot readynets; used when enqueueing new targets"""

    hot_readynets = set(db.session.execute(
        select(Heatmap.hashval).filter(
            Heatmap.hashval.in_(hashvals),
            Heatmap.count >= current_app.config['SNER_HEATMAP_HOT_LEVEL']
        )
    ).scalars().all())

    for thashval in (hashvals - hot_readynets):
        db.session.execute(
            pg_insert(Readynet)
            .values(queue_id=queue.id, hashval=thashval)
            .on_conflict_do_nothing(index_elements=[Readynet.queue_id, Readynet.hashval])
        )


def queue_enqueue(queue, targets):
    """enqueue targets to queue"""

    enqueued = []
    enqueued_hashvals = set()

    for target in filter(None, map(lambda x: x.strip(), targets)):
        thashval = target_hashval(target)
        enqueued.append({'queue_id': queue.id, 'target': target, 'hashval': thashval})
        enqueued_hashvals.add(thashval)

    if enqueued:
        wait_for_lock(Target.__tablename__, 0)
        db.session.execute(pg_insert(Target.__table__), enqueued)
        readynet_updates(queue, enqueued_hashvals)
        db.session.commit()


def queue_flush(queue):
    """queue flush; flush all targets from queue"""

    wait_for_lock(Target.__tablename__, 0)
    Target.query.filter(Target.queue_id == queue.id).delete()
    Readynet.query.filter(Readynet.queue_id == queue.id).delete()
    db.session.commit()  # release lock


def queue_prune(queue):
    """queue prune; delete all queue jobs"""

    for job in queue.jobs:
        job_delete(job)
    db.session.commit()


def queue_delete(queue):
    """queue delete; delete all jobs in cascade (deals with output files)"""

    for job in queue.jobs:
        job_delete(job)
    if os.path.exists(queue.data_abspath):
        os.rmdir(queue.data_abspath)
    db.session.delete(queue)
    db.session.commit()


def job_delete(job):
    """job delete; used by controller and respective command"""

    # deleting running job would corrupt heatmap
    if job.retval is None:
        current_app.logger.error('cannot delete running job %s', job.id)
        raise RuntimeError('cannot delete running job')

    if os.path.exists(job.output_abspath):
        os.remove(job.output_abspath)
    db.session.delete(job)
    db.session.commit()


def assignment_select_queue(queue_name, client_caps):
    """
    select queue for target assignment accounting client request constraints

    * queue must be active
    * client capabilities (caps) must conform queue requirements (reqs)
    * queue must have any rate-limit available targets/networks enqueued
    * must suffice client requested parameters (name)
    * queue is selected with priority in respect, but at random on same prio levels
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


def assignment_get(queue_name, client_caps):
    """
    assign job for agent

    * select suitable queue
    * select random readynet for queue (readynets reflects current rate-limit heatmap state)
    * pop random target within selected readynet
    * cleanup readynet if queue does not hold any target in same readynet
    * update rate-limit heatmap
    * remove all queues readynets if readynet become hot
    """

    assignment = {}  # nowork
    assigned_targets = []
    blacklist = ExclMatcher()

    # acquire lock
    if not wait_for_lock(Target.__tablename__, TIMEOUT_ASSIGN):
        return assignment

    # select queue
    queue = assignment_select_queue(queue_name, client_caps)
    if not queue:
        db.session.commit()  # release lock
        return assignment

    # assign targets
    while True:
        readynet_hashval = db.session.execute(
            select(Readynet.hashval)
            .filter(Readynet.queue_id == queue.id)
            .order_by(func.random())
            .limit(1)
        ).scalar()
        if not readynet_hashval:
            break

        target_id, target = db.session.execute(
            select(Target.id, Target.target)
            .filter(Target.queue_id == queue.id, Target.hashval == readynet_hashval)
            .order_by(func.random())
            .limit(1)
        ).first()

        db.session.execute(delete(Target.__table__).filter(Target.id == target_id))
        db.session.execute(
            delete(Readynet.__table__)
            .filter(
                Readynet.queue_id == queue.id,
                select(func.count(Target.id)).filter(Target.queue_id == queue.id, Target.hashval == readynet_hashval).scalar_subquery() == 0
            )
        )

        if blacklist.match(target):
            continue
        assigned_targets.append(target)
        heatmap_put(readynet_hashval)
        if len(assigned_targets) == queue.group_size:
            break

    # create job
    if assigned_targets:
        assignment = {
            'id': str(uuid4()),
            'config': {} if queue.config is None else yaml.safe_load(queue.config),
            'targets': assigned_targets
        }
        job = Job(id=assignment['id'], assignment=json.dumps(assignment), queue=queue)
        db.session.add(job)

    # release lock and respond to agent
    db.session.commit()
    return assignment


def job_process_output(request_json):
    """
    receive output from assigned job

    * for each target update rate-limit heatmap
    * if readynet of the target becomes cool activate it for all queues
    """

    try:
        jsonschema.validate(request_json, schema=sner.agent.protocol.output)
        job_id = request_json['id']
        retval = request_json['retval']
        output = base64.b64decode(request_json['output'])
    except (jsonschema.exceptions.ValidationError, binascii.Error):
        raise RuntimeError('Invalid request', HTTPStatus.BAD_REQUEST) from None

    # requests for invalid, deleted, repeated or clashing job ids are
    # silently discarded agent should delete the output on it's side as
    # well
    job = Job.query.filter(Job.id == job_id).one_or_none()
    if job and (job.retval is None):
        if not wait_for_lock(Target.__tablename__, TIMEOUT_OUTPUT):
            raise RuntimeError('Server busy', HTTPStatus.TOO_MANY_REQUESTS) from None

        job.retval = retval
        os.makedirs(os.path.dirname(job.output_abspath), exist_ok=True)
        with open(job.output_abspath, 'wb') as ftmp:
            ftmp.write(output)
        job.time_end = datetime.utcnow()

        for target in json.loads(job.assignment)['targets']:
            thashval = target_hashval(target)
            heatmap_pop(thashval)

        db.session.commit()  # commit job record and release lock

    return True
