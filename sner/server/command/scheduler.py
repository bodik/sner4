"""scheduler commands"""

import json
import sys
from ipaddress import ip_address, ip_network, summarize_address_range

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func

from sner.server import db
from sner.server.controller.scheduler.job import job_delete
from sner.server.model.scheduler import Job, Queue, Target, Task


def queuebyx(queueid):
    """get queue by id or name"""
    if queueid.isnumeric():
        queue = Queue.query.filter(Queue.id == int(queueid)).one_or_none()
    else:
        queue = Queue.query.filter(Queue.name == queueid).one_or_none()
    return queue


@click.group(name='scheduler', help='sner.server scheduler management')
def scheduler_command():
    """scheduler commands click group/container"""


# misc commands

@scheduler_command.command(name='enumips', help='enumerate ip address range')
@click.argument('targets', nargs=-1)
@click.option('--file', type=click.File('r'))
def enumips(targets, **kwargs):
    """enumerate ip address range"""

    targets = list(targets)
    if kwargs["file"]:
        targets += kwargs["file"].read().splitlines()
    for item in targets:
        for tmp in ip_network(item).hosts():
            print(tmp)


@scheduler_command.command(name='rangetocidr', help='convert range specified addr space to series of cidr')
@click.argument('start')
@click.argument('end')
def rangetocidr(start, end):
    """summarize net rage into cidrs"""

    for tmp in summarize_address_range(ip_address(start), ip_address(end)):
        print(tmp)


# queue commands

@scheduler_command.command(name='queue_list', help='queues listing')
@with_appcontext
def queue_list():
    """list queues"""

    listing = db.session.query(Queue.id, Queue.name, Task, func.count(Target.id)) \
        .outerjoin(Task).outerjoin(Target).group_by(Queue.id, Queue.name, Task).all()
    headers = ['id', 'name', 'task', 'targets']
    fmt = '%-4s %-20s %-40s %-8s'
    print(fmt % tuple(headers))
    for row in listing:
        print(fmt % row)


@scheduler_command.command(name='queue_enqueue', help='add targets to queue')
@click.argument('queue_id')
@click.argument('argtargets', nargs=-1)
@click.option('--file', type=click.File('r'))
@with_appcontext
def queue_enqueue(queue_id, argtargets, **kwargs):
    """enqueue targets to queue"""

    queue = queuebyx(queue_id)
    if not queue:
        current_app.logger.error('no such queue')
        sys.exit(1)

    argtargets = list(argtargets)
    if kwargs["file"]:
        argtargets += kwargs["file"].read().splitlines()
    targets = [{'target': target, 'queue_id': queue.id} for target in argtargets]
    db.session.bulk_insert_mappings(Target, targets)
    db.session.commit()
    sys.exit(0)


@scheduler_command.command(name='queue_flush', help='flush all targets from queue')
@click.argument('queue_id')
@with_appcontext
def queue_flush(queue_id):
    """flush targets from queue"""

    queue = queuebyx(queue_id)
    if not queue:
        current_app.logger.error('no such queue')
        sys.exit(1)

    db.session.query(Target).filter(Target.queue_id == queue.id).delete()
    db.session.commit()
    sys.exit(0)


# job commands

@scheduler_command.command(name='job_list', help='jobs listing')
@with_appcontext
def job_list():
    """list jobs"""

    headers = ['id', 'queue', 'retval', 'time_start', 'time_end', 'output_filename']
    fmt = '%-36s %-40s %6s %-20s %-20s %-40s'
    print(fmt % tuple(headers))
    for job in Job.query.all():
        print(fmt % (
            job.id,
            json.dumps(job.queue.name if job.queue else ''),
            job.retval,
            current_app.jinja_env.filters['datetime'](job.time_start),
            current_app.jinja_env.filters['datetime'](job.time_end),
            job.output))


@scheduler_command.command(name='job_delete', help='delete job')
@click.argument('job_id')
@with_appcontext
def job_delete_command(job_id):
    """job delete command stub"""

    job = Job.query.filter(Job.id == job_id).one_or_none()
    if not job:
        current_app.logger.error('no such job')
        sys.exit(1)

    sys.exit(job_delete(job))
