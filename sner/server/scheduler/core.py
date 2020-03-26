# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler shared functions
"""

import os
from ipaddress import ip_network

from sner.server.extensions import db
from sner.server.scheduler.models import Target


def enumerate_network(arg):
    """enumerate ip address range"""

    network = ip_network(arg, strict=False)
    data = list(map(str, network.hosts()))
    if network.prefixlen == network.max_prefixlen:
        data.append(str(network.network_address))
    return data


def queue_enqueue(queue, targets):
    """enqueue targets to queue"""

    enqueued = []
    for target in map(lambda x: x.strip(), targets):
        if target != '':
            enqueued.append({'target': target, 'queue_id': queue.id})
    db.session.bulk_insert_mappings(Target, enqueued)
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
