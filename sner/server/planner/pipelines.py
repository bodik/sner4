# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner planner pipelines impl
"""

from copy import deepcopy
from pathlib import Path
from shutil import copy2

from flask import current_app

from sner.server.planner.steps import registered_steps
from sner.server.scheduler.core import job_delete
from sner.server.scheduler.models import Job, Queue


def archive_job(job):
    """archive and delete job"""

    archive_dir = Path(current_app.config['SNER_VAR']) / 'planner_archive'
    archive_dir.mkdir(parents=True, exist_ok=True)
    copy2(job.output_abspath, archive_dir)
    job_delete(job)


class Context(dict):
    """context object"""


def run_queue_pipeline(config):
    """run queue processing pipeline"""

    current_app.logger.debug(f'run pipeline: {config}')
    queue = Queue.query.filter(Queue.name == config['queue']).one()

    for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
        ctx = Context()
        ctx['job'] = job

        for step_config in config['steps']:
            current_app.logger.debug(f'run step: {step_config}')
            args = deepcopy(step_config)
            step = args.pop('step')
            registered_steps[step](ctx, **args)

        archive_job(job)
        current_app.logger.debug(f'pipeline {config} processed for {job.id} ({queue.name})')


def run_standalone_pipeline(config):
    """run standalone pipeline"""

    current_app.logger.debug(f'run pipeline: {config}')
    ctx = Context()

    for step_config in config['steps']:
        current_app.logger.debug(f'run step: {step_config}')
        args = deepcopy(step_config)
        step = args.pop('step')
        registered_steps[step](ctx, **args)
