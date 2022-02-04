# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner planner pipeline steps
"""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network, IPv6Address
from pathlib import Path
from shutil import copy2

import yaml
from flask import current_app
from pytimeparse import parse as timeparse
from sqlalchemy import func, not_, or_

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.parser import REGISTERED_PARSERS
from sner.server.storage.core import import_parsed
from sner.server.scheduler.core import enumerate_network, filter_already_queued, JobManager, QueueManager
from sner.server.scheduler.models import Job, Queue
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import windowed_query


REGISTERED_STEPS = {}


def register_step(fnc):
    """register step function to registry"""

    if fnc.__name__ not in REGISTERED_STEPS:
        REGISTERED_STEPS[fnc.__name__] = fnc
    return fnc


class StopPipeline(Exception):
    """stop pipeline signal"""


class Context(dict):
    """context object"""

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


def run_steps(steps, ctx=None):
    """run steps in array of steps"""

    if not ctx:
        ctx = Context()

    for step_config in steps:
        current_app.logger.debug(f'run step: {step_config}')
        args = deepcopy(step_config)
        step_name = args.pop('step')
        ctx = REGISTERED_STEPS[step_name](ctx, **args)

    return ctx


@register_step
def stop_pipeline(_):
    """raises StopPipeline; used in tests"""
    raise StopPipeline


@register_step
def load_job(ctx, queue):
    """load one finished job from queue or signal stop to pipeline"""

    qref = Queue.query.filter(Queue.name == queue).one()
    job = Job.query.filter(Job.queue == qref, Job.retval == 0).first()
    if not job:
        raise StopPipeline()

    current_app.logger.info(f'load_job {job.id} ({qref.name})')
    ctx.job = job
    queue_module_config = yaml.safe_load(job.queue.config)
    parser = REGISTERED_PARSERS[queue_module_config['module']]
    ctx.data = parser.parse_path(job.output_abspath)

    return ctx


@register_step
def import_job(ctx):
    """import data to storage"""

    current_app.logger.info(f'import_job {ctx.job.id} ({ctx.job.queue.name})')
    import_parsed(ctx.data)

    return ctx


@register_step
def archive_job(ctx):
    """archive job step"""

    job = ctx.job
    job_id, queue_name = job.id, job.queue.name

    current_app.logger.info(f'archive_job {job_id} ({queue_name})')
    archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    copy2(job.output_abspath, archive_dir)
    JobManager.delete(job)

    return ctx


@register_step
def project_servicelist(ctx):
    """project service list from context data"""

    data = []
    for service in ctx.data.services.values():
        data.append(f'{service.proto}://{format_host_address(ctx.data.hosts[service.host_handle].address)}:{service.port}')
    ctx.data = data

    return ctx


@register_step
def project_hostlist(ctx):
    """project host list from context data"""

    data = []
    for host in ctx.data.hosts.values():
        data.append(f'{host.address}')
    ctx.data = data

    return ctx


@register_step
def filter_tarpits(ctx, threshold=200):
    """filter filter hosts with too much services detected"""

    host_services_count = defaultdict(int)
    for service in ctx.data.services.values():
        host_services_count[ctx.data.hosts[service.host_handle].address] += 1
    hosts_over_threshold = dict(filter(lambda x: x[1] > threshold, host_services_count.items()))

    if hosts_over_threshold:
        current_app.logger.info(f'filter_tarpits {ctx.job.id} {hosts_over_threshold}')

        for key, val in list(ctx.data.hosts.items()):
            if val.address in hosts_over_threshold:
                ctx.data.hosts.pop(key)

        for collection in ['services', 'vulns', 'notes']:
            for key, val in list(getattr(ctx.data, collection).items()):
                if val.host_handle.address in hosts_over_threshold:
                    getattr(ctx.data, collection).pop(key)

    return ctx


@register_step
def filter_netranges(ctx, netranges):
    """filter ctx data, whitelist only specified netranges"""

    whitelist = [ip_network(net) for net in netranges]
    data = [item for item in ctx.data if any(ip_address(item) in net for net in whitelist)]
    ctx.data = data

    return ctx


@register_step
def enqueue(ctx, queue):
    """enqueue to queue from context data"""

    if ctx.data:
        current_app.logger.info(f'enqueue {len(ctx.data)} targets to "{queue}"')
        queue = Queue.query.filter(Queue.name == queue).one()
        QueueManager.enqueue(queue, filter_already_queued(queue, ctx.data))

    return ctx


@register_step
def run_group(ctx, name):
    """run multiple steps defined by name"""

    return run_steps(current_app.config['SNER_PLANNER']['step_groups'][name], ctx)


@register_step
def enumerate_ipv4(ctx, netranges):
    """enumerates list of netranges"""

    ctx.data = []
    for netrange in netranges:
        ctx.data += enumerate_network(netrange)

    if ctx.data:
        current_app.logger.info(f'enumerate_ipv4, enumerated {len(ctx.data)} items')

    return ctx


@register_step
def rescan_services(ctx, interval):
    """rescan services from storage; update known services info"""

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(interval))
    query = Service.query.filter(or_(Service.rescan_time < rescan_horizont, Service.rescan_time == None))  # noqa: E501,E711  pylint: disable=singleton-comparison

    rescan, ids = [], []
    for service in windowed_query(query, Service.id):
        item = f'{service.proto}://{format_host_address(service.host.address)}:{service.port}'
        rescan.append(item)
        ids.append(service.id)
    # orm is bypassed for performance reasons in case of large rescans
    update_statement = Service.__table__.update().where(Service.id.in_(ids)).values(rescan_time=now)
    db.session.execute(update_statement)
    db.session.commit()
    db.session.expire_all()

    ctx.data = rescan
    if rescan:
        current_app.logger.info(f'rescan_services, rescan {len(rescan)} items')

    return ctx


@register_step
def rescan_hosts(ctx, interval):
    """rescan hosts from storage; discovers new services on hosts"""

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(interval))
    query = Host.query.filter(or_(Host.rescan_time < rescan_horizont, Host.rescan_time == None))  # noqa: E711  pylint: disable=singleton-comparison

    rescan, ids = [], []
    for host in windowed_query(query, Host.id):
        rescan.append(host.address)
        ids.append(host.id)
    # orm is bypassed for performance reasons in case of large rescans
    update_statement = Host.__table__.update().where(Host.id.in_(ids)).values(rescan_time=now)
    db.session.execute(update_statement)
    db.session.commit()
    db.session.expire_all()

    ctx.data = rescan
    if rescan:
        current_app.logger.info(f'rescan_hosts, rescan {len(rescan)} items')

    return ctx


@register_step
def storage_ipv6_enum(ctx):
    """discover ipv6 hosts via enumeration around already discovered storage addresses"""

    targets = set()
    for host in Host.query.filter(func.family(Host.address) == 6).order_by(Host.address).all():
        exploded = IPv6Address(host.address).exploded
        # do not enumerate EUI-64 hosts/nets
        if exploded[27:32] == 'ff:fe':
            continue

        # generate mask for scan6 tool
        exploded = exploded.split(':')
        exploded[-1] = '0-ffff'
        target = ':'.join(exploded)

        targets.add(target)

    ctx.data = targets
    if targets:
        current_app.logger.info(f'storage_ipv6_enum, queued {len(targets)} items')

    return ctx


@register_step
def storage_cleanup(ctx):
    """clean up storage from various import artifacts"""

    # NOTE: Services must be deleted via ORM otherwise relationship defined
    # cascades (vulns, notes) would break. Hosts could be because of
    # non-nullable foregin keys, but anyway we'll delete them with ORM too.

    # remove any but open:* state services
    query = Service.query.filter(not_(Service.state.ilike('open:%')))
    for service in query.all():
        db.session.delete(service)  # must not bypass orm due to relationship defined cascades to vulns and notes
    db.session.commit()

    # remove hosts without any data attribute, service, vuln or note
    query = db.session.query(Host.id).filter(or_(Host.os == '', Host.os == None), or_(Host.comment == '', Host.comment == None))  # noqa: E501,E711  pylint: disable=singleton-comparison
    hosts_noinfo = [dbid for dbid, in query.all()]

    hosts_noservices = [dbid for dbid, in db.session.query(Host.id).outerjoin(Service).having(func.count(Service.id) == 0).group_by(Host.id).all()]
    hosts_novulns = [dbid for dbid, in db.session.query(Host.id).outerjoin(Vuln).having(func.count(Vuln.id) == 0).group_by(Host.id).all()]
    hosts_nonotes = [dbid for dbid, in db.session.query(Host.id).outerjoin(Note).having(func.count(Note.id) == 0).group_by(Host.id).all()]

    hosts_to_delete = list(set(hosts_noinfo) & set(hosts_noservices) & set(hosts_novulns) & set(hosts_nonotes))
    for host in Host.query.filter(Host.id.in_(hosts_to_delete)).all():
        db.session.delete(host)
    db.session.commit()

    # also remove all hosts not having any info but one note xtype hostnames
    hosts_only_one_note = [dbid for dbid, in db.session.query(Host.id).outerjoin(Note).having(func.count(Note.id) == 1).group_by(Host.id).all()]
    query = db.session.query(Host.id).join(Note).filter(Host.id.in_(hosts_only_one_note), Note.xtype == 'hostnames')
    hosts_only_note_hostnames = [dbid for dbid, in query.all()]

    hosts_to_delete = list(set(hosts_noinfo) & set(hosts_noservices) & set(hosts_novulns) & set(hosts_only_note_hostnames))
    for host in Host.query.filter(Host.id.in_(hosts_to_delete)).all():
        db.session.delete(host)
    db.session.commit()

    current_app.logger.debug('finished storage_cleanup')

    return ctx
