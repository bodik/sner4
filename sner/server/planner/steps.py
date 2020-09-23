# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner planner pipeline steps
"""

from datetime import datetime, timedelta
from ipaddress import ip_address, IPv4Address, IPv6Address, IPv6Network
from pathlib import Path
from shutil import copy2

import yaml
from flask import current_app
from pytimeparse import parse as timeparse
from sqlalchemy import func, not_, or_

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.parser import registered_parsers
from sner.server.storage.core import import_parsed
from sner.server.scheduler.core import enumerate_network, filter_already_queued, job_delete, queue_enqueue
from sner.server.scheduler.models import Job, Queue
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import windowed_query


registered_steps = {}  # pylint: disable=invalid-name


def register_step(fnc):
    """register step function to registry"""

    if fnc.__name__ not in registered_steps:
        registered_steps[fnc.__name__] = fnc
    return fnc


def should_run(name, interval):
    """checks .lastrun and returns true if calle should run acording to interval"""

    lastrun_path = Path(current_app.config['SNER_VAR']) / f'{name}.lastrun'
    if lastrun_path.exists():
        lastrun = datetime.fromisoformat(lastrun_path.read_text())
        if (datetime.utcnow().timestamp() - lastrun.timestamp()) < interval:
            return False
    return True


def update_lastrun(name):
    """update .lastrun file"""

    lastrun_path = Path(current_app.config['SNER_VAR']) / f'{name}.lastrun'
    lastrun_path.write_text(datetime.utcnow().isoformat())


class StopPipeline(Exception):
    """stop pipeline signal"""


@register_step
def debug(ctx):
    """debug current context"""

    current_app.logger.info(ctx)


@register_step
def stop_pipeline(ctx):
    """stop pipeline"""

    raise StopPipeline()


@register_step
def load_job(ctx, queue):
    """load one finished job from queue or signal stop to pipeline"""

    qref = Queue.query.filter(Queue.name == queue).one()
    job = Job.query.filter(Job.queue == qref, Job.retval == 0).first()
    if not job:
        raise StopPipeline()

    ctx['job'] = job
    queue_module_config = yaml.safe_load(job.queue.config)
    parser = registered_parsers[queue_module_config['module']]
    ctx['data'] = dict(zip(['hosts', 'services', 'vulns', 'notes'], parser.parse_path(job.output_abspath)))


@register_step
def import_job(ctx):
    """import data to storage"""

    import_parsed(**ctx['data'])


@register_step
def project_servicelist(ctx):
    """project service list from context data"""

    data = []
    for service in ctx['data']['services']:
        data.append(f'{service.proto}://{service.handle["host"]}:{service.port}')
    ctx['data'] = data


@register_step
def project_hostlist(ctx):
    """project host list from context data"""

    data = []
    for host in ctx['data']['hosts']:
        data.append(f'{host.address}')
    ctx['data'] = data


@register_step
def filter_netranges(ctx, netranges):
    """filter ctx data, whitelist only specified netranges"""

    whitelist = [IPv6Network(net) for net in netranges]
    data = [item for item in ctx['data'] if any([IPv6Address(item) in net for net in whitelist])]
    ctx['data'] = data


@register_step
def enqueue(ctx, queue):
    """enqueue to queue from context data"""

    queue = Queue.query.filter(Queue.name == queue).one()
    queue_enqueue(queue, filter_already_queued(queue, ctx['data']))


@register_step
def archive_job(ctx):
    """archive job step"""

    job = ctx['job']
    job_id, queue_name = job.id, job.queue.name

    archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    copy2(job.output_abspath, archive_dir)
    job_delete(job)

    current_app.logger.info(f'archived job {job_id} ({queue_name})')


@register_step
def cleanup_storage(_):
    """clean up storage from various import artifacts"""

    # remove any but open:* state services
    query_services = Service.query.filter(not_(Service.state.ilike('open:%')))
    for service in query_services.all():
        db.session.delete(service)
    db.session.commit()

    # remove hosts without any data attribute, service, vuln or note
    services_count = func.count(Service.id)
    vulns_count = func.count(Vuln.id)
    notes_count = func.count(Note.id)
    query_hosts = Host.query \
        .outerjoin(Service, Host.id == Service.host_id).outerjoin(Vuln, Host.id == Vuln.host_id).outerjoin(Note, Host.id == Note.host_id) \
        .filter(
            or_(Host.os == '', Host.os == None),  # noqa: E711  pylint: disable=singleton-comparison
            or_(Host.comment == '', Host.comment == None)  # noqa: E711  pylint: disable=singleton-comparison
        ) \
        .having(services_count == 0).having(vulns_count == 0).having(notes_count == 0).group_by(Host.id)

    for host in query_hosts.all():
        db.session.delete(host)
    db.session.commit()
    current_app.logger.debug(f'storage cleaned')


@register_step
def rescan_services(_, interval, queue4, queue6):
    """rescan services from storage; update known services info"""

    queue4 = Queue.query.filter(Queue.name == queue4).one()
    queue6 = Queue.query.filter(Queue.name == queue6).one()

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(interval))
    query = Service.query.filter(or_(Service.rescan_time < rescan_horizont, Service.rescan_time == None))  # noqa: E501,E711  pylint: disable=singleton-comparison

    rescan4, rescan6, ids = [], [], []
    for service in windowed_query(query, Service.id):
        item = f'{service.proto}://{format_host_address(service.host.address)}:{service.port}'
        if isinstance(ip_address(service.host.address), IPv4Address):
            rescan4.append(item)
            ids.append(service.id)
        elif isinstance(ip_address(service.host.address), IPv6Address):
            rescan6.append(item)
            ids.append(service.id)
    # orm is bypassed for performance reasons in case of large rescans
    update_statement = Service.__table__.update().where(Service.id.in_(ids)).values(rescan_time=now)
    db.session.execute(update_statement)
    db.session.commit()
    db.session.expire_all()

    rescan4 = filter_already_queued(queue4, rescan4)
    queue_enqueue(queue4, rescan4)
    rescan6 = filter_already_queued(queue6, rescan6)
    queue_enqueue(queue6, rescan6)

    if rescan4 or rescan6:
        current_app.logger.info(f'rescan_services, rescan4 {len(rescan4)}, rescan6 {len(rescan6)}')


@register_step
def rescan_hosts(_, interval, queue4, queue6):
    """rescan hosts from storage; discovers new services on hosts"""

    queue4 = Queue.query.filter(Queue.name == queue4).one()
    queue6 = Queue.query.filter(Queue.name == queue6).one()

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(interval))
    query = Host.query.filter(or_(Host.rescan_time < rescan_horizont, Host.rescan_time == None))  # noqa: E711  pylint: disable=singleton-comparison

    rescan4, rescan6, ids = [], [], []
    for host in windowed_query(query, Host.id):
        if isinstance(ip_address(host.address), IPv4Address):
            rescan4.append(host.address)
            ids.append(host.id)
        elif isinstance(ip_address(host.address), IPv6Address):
            rescan6.append(host.address)
            ids.append(host.id)
    # orm is bypassed for performance reasons in case of large rescans
    update_statement = Host.__table__.update().where(Host.id.in_(ids)).values(rescan_time=now)
    db.session.execute(update_statement)
    db.session.commit()
    db.session.expire_all()

    rescan4 = filter_already_queued(queue4, rescan4)
    queue_enqueue(queue4, rescan4)
    rescan6 = filter_already_queued(queue6, rescan6)
    queue_enqueue(queue6, rescan6)

    if rescan4 or rescan6:
        current_app.logger.info(f'rescan_hosts, rescan4 {len(rescan4)}, rescan6 {len(rescan6)}')


@register_step
def discover_ipv4(_, interval, netranges, queue):
    """enqueues all netranges into discovery queue"""

    queue = Queue.query.filter(Queue.name == queue).one()

    if not should_run('discover_ipv4', timeparse(interval)):
        return

    count = 0
    for netrange in netranges:
        targets = filter_already_queued(queue, enumerate_network(netrange))
        count += len(targets)
        queue_enqueue(queue, targets)

    update_lastrun('discover_ipv4')

    if count:
        current_app.logger.info(f'discover_ipv4, queued {count}')


@register_step
def discover_ipv6_dns(_, interval, netranges, queue):
    """enqueues all netranges into dns discovery queue"""

    if not should_run('discover_ipv6_dns', timeparse(interval)):
        return

    queue = Queue.query.filter(Queue.name == queue).one()
    count = 0
    for netrange in netranges:
        targets = filter_already_queued(queue, enumerate_network(netrange))
        count += len(targets)
        queue_enqueue(queue, targets)

    if count:
        current_app.logger.info(f'discover_ipv6_dns, queued {count}')
    update_lastrun('discover_ipv6_dns')


@register_step
def discover_ipv6_enum(_, interval, queue):
    """enqueues ranged derived from storage registered ipv6 addresses"""

    if not should_run('discover_ipv6_enum', timeparse(interval)):
        return

    queue = Queue.query.filter(Queue.name == queue).one()
    targets = set()
    query = Host.query.filter(func.family(Host.address) == 6).order_by(Host.address)
    for host in query.all():
        exploded = IPv6Address(host.address).exploded
        # do not enumerate EUI-64 hosts/nets
        if exploded[27:32] == 'ff:fe':
            continue

        exploded = exploded.split(':')
        exploded[-1] = '0-ffff'
        target = ':'.join(exploded)

        targets.add(target)

    targets = filter_already_queued(queue, targets)
    queue_enqueue(queue, targets)

    if targets:
        current_app.logger.info(f'discover_ipv6_enum, queued {len(targets)}')
    update_lastrun('discover_ipv6_enum')
