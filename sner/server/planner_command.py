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
from sqlalchemy import func, not_, or_

from sner.server.extensions import db
from sner.server.parser import registered_parsers
from sner.server.scheduler.core import job_delete, queue_enqueue
from sner.server.scheduler.models import Job, Queue
from sner.server.storage.models import Host, Note, Service, Vuln


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

    def run(self, loopsleep, oneshot):
        """run planner loop"""

        self.loop = True
        with self.terminate_context():
            while self.loop:
                self._process_workflows()
                self._cleanup_storage()
                if oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    sleep(loopsleep)

    def _process_workflows(self):
        """process workflows over finished jobs"""

        for queue in Queue.query.filter(Queue.workflow is not None).all():
            for job in Job.query.filter(Job.queue == queue, Job.retval == 0).all():
                try:
                    workflow = yaml.safe_load(queue.workflow)
                    if workflow['step'] == 'enqueue_servicelist':
                        self._step_enqueue_servicelist(job)
                    elif workflow['step'] == 'import':
                        self._step_import(job)
                    else:
                        raise ValueError('invalid workflow step, queue %s' % queue)
                except Exception as e:  # pylint: disable=broad-except  ; a lot of things can go wrong during workflow, skip job and recover
                    self.log.exception('workflow processing error', e)

    def _step_enqueue_servicelist(self, job):
        """perform step enqueue_service_list"""

        workflow = yaml.safe_load(job.queue.workflow)
        next_queue = Queue.query.filter(Queue.name == workflow['queue']).one()
        config = yaml.safe_load(job.queue.config)
        parser = registered_parsers[config['module']]
        service_list = list(map(
            lambda x: x.service,
            filter(
                lambda x: not (x.state.startswith('filtered') or x.state.startswith('closed')),
                parser.service_list(job.output_abspath)
            )
        ))
        queue_enqueue(next_queue, service_list)
        copy2(job.output_abspath, self.archive_dir)
        job_delete(job)

    def _step_import(self, job):
        """perform step enqueue_service_list"""

        config = yaml.safe_load(job.queue.config)
        parser = registered_parsers[config['module']]
        parser.import_file(job.output_abspath)
        copy2(job.output_abspath, self.archive_dir)
        job_delete(job)

    def _cleanup_storage(self):  # pylint: disable=no-self-use
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


@click.command(name='planner', help='run planner daemon')
@with_appcontext
@click.option('--oneshot', is_flag=True)
@click.option('--loopsleep', default=60)
def command(**kwargs):
    """run planner daemon"""

    Planner().run(float(kwargs.get('loopsleep')), kwargs.get('oneshot'))
