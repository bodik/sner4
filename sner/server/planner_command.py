# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server planner command module
"""

from pathlib import Path
from shutil import copy2
from time import sleep

import click
import yaml
from flask import current_app
from flask.cli import with_appcontext
from schema import Or, Schema

from sner.server.parser import registered_parsers
from sner.server.scheduler.core import job_delete, queue_enqueue
from sner.server.scheduler.models import Job, Queue


PLANNER_LOOP_SLEEP = 60

WORKFLOW_SCHEMA = Schema(Or(
    {
        'step': 'enqueue_servicelist',
        'queue': str
    },
    {
        'step': 'import'
    }
))


@click.command(name='planner', help='run planner daemon')
@with_appcontext
@click.option('--oneshot', is_flag=True)
def command(**kwargs):
    """run planner daemon"""

    archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
    archive_dir.mkdir(parents=True, exist_ok=True)

    loop = True
    while loop:
        for queue in Queue.query.filter(Queue.workflow is not None).all():
            for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
                try:
                    queue_config = yaml.safe_load(queue.config)
                    workflow_config = yaml.safe_load(queue.workflow)
                except yaml.YAMLError as e:
                    current_app.logger.error(f'invalid queue config, {str(e)}')
                    continue

                try:
                    parser = registered_parsers[queue_config['module']]
                except KeyError:
                    current_app.logger.error(f'parser for queue module missing, queue %s', queue)
                    continue

                if workflow_config['step'] == 'enqueue_servicelist':
                    next_queue = Queue.query.filter(Queue.name == workflow_config['queue']).one_or_none()
                    if not next_queue:
                        current_app.logger.error(f'invalid next queue "%s"', workflow_config['queue'])
                        continue
                    queue_enqueue(next_queue, parser.service_list(job.output_abspath, exclude_states=['filtered', 'closed']))
                    copy2(job.output_abspath, archive_dir)
                    job_delete(job)

                elif workflow_config['step'] == 'import':
                    parser.import_file(job.output_abspath)
                    copy2(job.output_abspath, archive_dir)
                    job_delete(job)

                else:
                    current_app.logger.error('invalid workflow config, queue %s', queue)

        sleep(PLANNER_LOOP_SLEEP)
        if kwargs['oneshot']:
            loop = False
