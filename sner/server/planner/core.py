# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core
"""

import logging
import signal
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import sleep

from flask import current_app
from pytimeparse import parse as timeparse
from schema import Or, Schema

from sner.server.extensions import db
from sner.server.planner.steps import run_steps, StopPipeline


PIPELINE_CONFIG_SCHEMA = Schema(Or(
    {'type': 'queue', 'steps': list},
    {'type': 'interval', 'name': str, 'interval': str, 'steps': list},
    {'type': 'generic', 'steps': list}
))


def run_pipeline(config):
    """
    run pipeline, queue pipelines runs until stop is signaled
    """

    if config['type'] == 'queue':
        run_queue_pipeline(config)
    elif config['type'] == 'interval':
        run_interval_pipeline(config)
    else:
        run_steps(config['steps'])


def run_queue_pipeline(config):
    """run queue pipeline"""

    try:
        while True:
            run_steps(config['steps'])
    except StopPipeline:
        return


def run_interval_pipeline(config):
    """run interval pipeline"""

    name = config['name']
    interval = config['interval']
    lastrun_path = Path(current_app.config['SNER_VAR']) / f'lastrun.{name}'

    if lastrun_path.exists():
        lastrun = datetime.fromisoformat(lastrun_path.read_text())
        if (datetime.utcnow().timestamp() - lastrun.timestamp()) < timeparse(interval):
            return

    try:
        run_steps(config['steps'])
    except StopPipeline:
        # stop_pipeline is emited during tests to check backoff interval
        pass

    lastrun_path.write_text(datetime.utcnow().isoformat())


class Planner:
    """planner"""

    LOOPSLEEP = 60

    def __init__(self, oneshot=False):
        self.log = current_app.logger
        self.log.setLevel(logging.DEBUG if current_app.config['DEBUG'] else logging.INFO)

        self.original_signal_handlers = {}
        self.loop = None
        self.oneshot = oneshot

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

    def run(self):
        """run planner loop"""

        self.loop = True
        config = current_app.config['SNER_PLANNER']['pipelines']

        with self.terminate_context():
            while self.loop:
                for pipeline in config:
                    try:
                        PIPELINE_CONFIG_SCHEMA.validate(pipeline)
                        run_pipeline(pipeline)
                    except Exception as e:  # pylint: disable=broad-except  ; any exception can be raised during pipeline processing
                        current_app.logger.error(f'pipeline failed, {pipeline}, {repr(e)}', exc_info=True)
                db.session.close()

                if self.oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    # support for long loops, but allow fast shutdown
                    for _ in range(self.LOOPSLEEP):
                        if self.loop:
                            sleep(1)
