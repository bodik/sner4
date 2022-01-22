# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler shared functions
"""

import os
from ipaddress import ip_network
from random import random

from sner.server.extensions import db
from sner.server.scheduler.heatmap import Heatmap
from sner.server.scheduler.models import Target
from sner.server.utils import windowed_query


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

    current_targets = {x[0]: 0 for x in windowed_query(db.session.query(Target.target).filter(Target.queue == queue), Target.id)}
    targets = [tgt for tgt in targets if tgt not in current_targets]
    return targets


def queue_enqueue(queue, targets):
    """enqueue targets to queue"""

    enqueued = []
    for target in map(lambda x: x.strip(), targets):
        if target != '':
            enqueued.append({'target': target, 'hashval': Heatmap.hashval(target), 'rand': random(), 'queue_id': queue.id})
    if enqueued:
        db.session.execute(Target.__table__.insert().values(enqueued))
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

    if os.path.exists(job.output_abspath):
        os.remove(job.output_abspath)
    db.session.delete(job)
    db.session.commit()
