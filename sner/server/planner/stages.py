# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner stages impl
"""

from datetime import datetime, timedelta
from ipaddress import ip_address, IPv4Address, IPv6Address
from pathlib import Path
from shutil import copy2

import celery
import yaml
from flask import current_app
from pytimeparse import parse as timeparse
from sqlalchemy import func, not_, or_

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.parser import registered_parsers
from sner.server.scheduler.core import enumerate_network, job_delete, queue_enqueue
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import windowed_query


def archive_job(job):
    """archive and delete job"""

    archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    copy2(job.output_abspath, archive_dir)
    job_delete(job)


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


@celery.task(bind=True)
def shutdown_test_helper(self):  # pragma: nocover  ; running over celery prefork worker
    """utility task used in tests"""

    celery.current_app.control.revoke(self.request.id)  # prevent this task from being executed again
    celery.current_app.control.shutdown()


@celery.task()
def enqueue_servicelist():
    """enqueue_servicelist stage"""

    for qname, next_qname in current_app.config['SNER_PLANNER']['enqueue_servicelist']:
        queue = Queue.query.filter(Queue.name == qname).one()
        queue_module_config = yaml.safe_load(queue.config)
        parser = registered_parsers[queue_module_config['module']]
        next_queue = Queue.query.filter(Queue.name == next_qname).one()

        for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
            service_list = list(map(
                lambda x: x.service,
                filter(
                    lambda x: not (x.state.startswith('filtered') or x.state.startswith('closed')),
                    parser.service_list(job.output_abspath)
                )
            ))
            queue_enqueue(next_queue, service_list)
            archive_job(job)
            current_app.logger.debug(f'enqueue_servicelist requeued {job.id} ({queue.name})')
    db.session.close()


@celery.task()
def enqueue_hostlist():
    """enqueue_hostlist stage"""

    for qname, next_qname in current_app.config['SNER_PLANNER']['enqueue_hostlist']:
        queue = Queue.query.filter(Queue.name == qname).one()
        queue_module_config = yaml.safe_load(queue.config)
        parser = registered_parsers[queue_module_config['module']]
        next_queue = Queue.query.filter(Queue.name == next_qname).one()

        for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
            host_list = parser.host_list(job.output_abspath)
            queue_enqueue(next_queue, host_list)
            archive_job(job)
            current_app.logger.debug(f'enqueue_hostlist requeued {job.id} ({queue.name})')
    db.session.close()


@celery.task()
def import_jobs():
    """import queue jobs"""

    do_cleanup = False

    for qname in current_app.config['SNER_PLANNER']['import_jobs']:
        queue = Queue.query.filter(Queue.name == qname).one()
        queue_module_config = yaml.safe_load(queue.config)
        parser = registered_parsers[queue_module_config['module']]

        for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
            do_cleanup = True
            parser.import_file(job.output_abspath)
            archive_job(job)
            current_app.logger.debug(f'import_jobs imported {job.id} ({queue.name})')

    if do_cleanup:
        cleanup_storage()
    db.session.close()


def cleanup_storage():
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
    current_app.logger.debug('cleanup_storage done')


def filter_already_queued(queue, targets):
    """filters already queued targets"""

    current_targets = {x[0]: 0 for x in windowed_query(db.session.query(Target.target).filter(Target.queue == queue), Target.id, 5000)}
    targets = [tgt for tgt in targets if tgt not in current_targets]
    return targets


@celery.task()
def rescan_services():
    """rescan services from storage; update known services info"""

    config = current_app.config['SNER_PLANNER']['rescan_services']
    queue4 = Queue.query.filter(Queue.name == config['queue4']).one()
    queue6 = Queue.query.filter(Queue.name == config['queue6']).one()

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(config['interval']))
    query = Service.query.filter(or_(Service.rescan_time < rescan_horizont, Service.rescan_time == None))  # noqa: E501,E711  pylint: disable=singleton-comparison

    rescan4, rescan6, ids = [], [], []
    for service in windowed_query(query, Service.id, 5000):
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
        current_app.logger.debug(f'rescan_services, rescan4 {len(rescan4)}, rescan6 {len(rescan6)}')
    db.session.close()


@celery.task()
def rescan_hosts():
    """rescan hosts from storage; discovers new services on hosts"""

    config = current_app.config['SNER_PLANNER']['rescan_hosts']
    queue4 = Queue.query.filter(Queue.name == config['queue4']).one()
    queue6 = Queue.query.filter(Queue.name == config['queue6']).one()

    now = datetime.utcnow()
    rescan_horizont = now - timedelta(seconds=timeparse(config['interval']))
    query = Host.query.filter(or_(Host.rescan_time < rescan_horizont, Host.rescan_time == None))  # noqa: E711  pylint: disable=singleton-comparison

    rescan4, rescan6, ids = [], [], []
    for host in windowed_query(query, Host.id, 5000):
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
        current_app.logger.debug(f'rescan_hosts, rescan4 {len(rescan4)}, rescan6 {len(rescan6)}')
    db.session.close()


@celery.task()
def discover_ipv4():
    """enqueues all netranges into discovery queue"""

    config = current_app.config['SNER_PLANNER']['discover_ipv4']
    queue = Queue.query.filter(Queue.name == config['queue']).one()

    if not should_run('discover_ipv4', timeparse(config['interval'])):
        return

    count = 0
    for netrange in config['netranges']:
        targets = filter_already_queued(queue, enumerate_network(netrange))
        count += len(targets)
        queue_enqueue(queue, targets)

    update_lastrun('discover_ipv4')

    if count:
        current_app.logger.debug(f'discover_ipv4, queued {count}')
    db.session.close()


@celery.task()
def discover_ipv6_dns():
    """enqueues all netranges into dns discovery queue"""

    config = current_app.config['SNER_PLANNER']['discover_ipv6_dns']
    queue = Queue.query.filter(Queue.name == config['queue']).one()

    if not should_run('discover_ipv6_dns', timeparse(config['interval'])):
        return

    count = 0
    for netrange in config['netranges']:
        targets = filter_already_queued(queue, enumerate_network(netrange))
        count += len(targets)
        queue_enqueue(queue, targets)

    update_lastrun('discover_ipv6_dns')

    if count:
        current_app.logger.debug(f'discover_ipv6_dns, queued {count}')
    db.session.close()


@celery.task()
def discover_ipv6_enum():
    """enqueues ranged derived from storage registered ipv6 addresses"""

    config = current_app.config['SNER_PLANNER']['discover_ipv6_enum']
    queue = Queue.query.filter(Queue.name == config['queue']).one()

    if not should_run('discover_ipv6_enum', timeparse(config['interval'])):
        return

    targets = set()
    query = Host.query.filter(func.family(Host.address) == 6).order_by(Host.address)
    for host in query.all():
        exploded = IPv6Address(host.address).exploded.split(':')
        exploded[-1] = '0-ffff'
        target = ':'.join(exploded)
        targets.add(target)

    targets = filter_already_queued(queue, targets)
    queue_enqueue(queue, targets)

    update_lastrun('discover_ipv6_enum')

    if targets:
        current_app.logger.debug(f'discover_ipv6_enum, queued {len(targets)}')
    db.session.close()
