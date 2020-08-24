# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner commands
"""

from warnings import filterwarnings
from pathlib import Path

import celery
import click
from flask import current_app
from flask.cli import with_appcontext
from pytimeparse import parse as timeparse

import sner.server.planner.stages


@click.group(name='planner', help='sner.server planner commands')
def command():
    """planner commands container"""


def add_stage(schedule, taskref):
    """adds stage/task to scheduler with logging"""

    name = taskref.task.split('.')[-1]
    celery.current_app.add_periodic_task(schedule, taskref, name=name)
    current_app.logger.info('add_task: %s, %s', name, schedule)


@command.command(name='run', help='run planner daemon')
@with_appcontext
@click.option('--debug', is_flag=True)
@click.option('--test', is_flag=True)
def run(**kwargs):
    """run planner daemon"""

    config = current_app.config['SNER_PLANNER']

    if 'import_jobs' in config:
        add_stage(60, sner.server.planner.stages.import_jobs.s())

    if 'enqueue_servicelist' in config:
        add_stage(60, sner.server.planner.stages.enqueue_servicelist.subtask())

    if 'enqueue_hostlist' in config:
        add_stage(60, sner.server.planner.stages.enqueue_hostlist.subtask())

    if 'rescan_services' in config:
        schedule = min(600, timeparse(config['rescan_services']['interval']))
        add_stage(schedule, sner.server.planner.stages.rescan_services.subtask())

    if 'rescan_hosts' in config:
        schedule = min(600, timeparse(config['rescan_hosts']['interval']))
        add_stage(schedule, sner.server.planner.stages.rescan_hosts.subtask())

    if 'discover_ipv4' in config:
        schedule = min(600, timeparse(config['discover_ipv4']['interval']))
        add_stage(schedule, sner.server.planner.stages.discover_ipv4.subtask())

    if 'discover_ipv6_dns' in config:
        schedule = min(600, timeparse(config['discover_ipv6_dns']['interval']))
        add_stage(schedule, sner.server.planner.stages.discover_ipv6_dns.subtask())

    if 'discover_ipv6_enum' in config:
        schedule = min(600, timeparse(config['discover_ipv6_enum']['interval']))
        add_stage(schedule, sner.server.planner.stages.discover_ipv6_enum.subtask())

    if kwargs['test']:
        add_stage(0.1, sner.server.planner.stages.shutdown_test_helper.subtask())

    filterwarnings('ignore', '.*')
    schedule_db_path = Path(current_app.config['SNER_VAR']) / 'planner_celerybeat_schedule'
    args = ['worker', '--concurrency', '1', '--purge', '--beat', '--schedule', str(schedule_db_path)]
    if kwargs['debug']:
        args += ['--loglevel', 'DEBUG']
    celery.current_app.worker_main(args)
