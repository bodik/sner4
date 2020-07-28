# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server planner command module

Planner handles finished jobs acording to queue workflow configuration. The
main task is to requeue discovered targets into subsequent queues or import
scan results into storage. Workflow configuration must be acording to
WORKFLOW_SCHEMA schema.
"""

import signal
from contextlib import contextmanager
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


WORKFLOW_SCHEMA = Schema(Or(
    {
        'step': 'enqueue_servicelist',
        'queue': str
    },
    {
        'step': 'import'
    }
))


class Planner:
    """planner"""

    def __init__(self):
        self.log = current_app.logger.getChild('sner.server.planner')
        self.original_signal_handlers = {}
        self.loop = None
        self.archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def terminate_context(self):
        """terminate context manager; should restore handlers despite of underlying code exceptions"""

        # break pylint duplicate-code
        self.original_signal_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self.terminate)
        self.original_signal_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self.terminate)
        try:
            # break pylint duplicate-code
            yield
        finally:
            signal.signal(signal.SIGINT, self.original_signal_handlers[signal.SIGINT])
            signal.signal(signal.SIGTERM, self.original_signal_handlers[signal.SIGTERM])

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """terminate at once"""

        self.log.info('terminate')
        self.loop = False

    def process_queues(self):
        """process queues"""

        for queue in Queue.query.filter(Queue.workflow is not None).all():
            for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
                try:
                    queue_config = yaml.safe_load(queue.config)
                    workflow_config = yaml.safe_load(queue.workflow)
                except yaml.YAMLError as e:
                    self.log.error(f'invalid queue config, {str(e)}')
                    continue

                try:
                    parser = registered_parsers[queue_config['module']]
                except KeyError:
                    self.log.error(f'parser for queue module missing, queue %s', queue)
                    continue

                if workflow_config['step'] == 'enqueue_servicelist':
                    next_queue = Queue.query.filter(Queue.name == workflow_config['queue']).one_or_none()
                    if not next_queue:
                        self.log.error(f'invalid next queue "%s"', workflow_config['queue'])
                        continue
                    queue_enqueue(next_queue, parser.service_list(job.output_abspath, exclude_states=['filtered', 'closed']))
                    copy2(job.output_abspath, self.archive_dir)
                    job_delete(job)

                elif workflow_config['step'] == 'import':
                    parser.import_file(job.output_abspath)
                    copy2(job.output_abspath, self.archive_dir)
                    job_delete(job)

                else:
                    self.log.error('invalid workflow config, queue %s', queue)

    def run(self, loopsleep, oneshot):
        """run planner loop"""

        self.loop = True
        with self.terminate_context():
            while self.loop:
                self.process_queues()
                if oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    sleep(loopsleep)


@click.command(name='planner', help='run planner daemon')
@with_appcontext
@click.option('--oneshot', is_flag=True)
@click.option('--loopsleep', default=30)
def command(**kwargs):
    """run planner daemon"""

    Planner().run(float(kwargs.get('loopsleep')), kwargs.get('oneshot'))
