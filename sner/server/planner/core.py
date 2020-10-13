# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core
"""

import logging
import signal
from contextlib import contextmanager
from copy import deepcopy
from time import sleep

from flask import current_app
from schema import Schema, Or

from sner.server.extensions import db
from sner.server.planner.steps import registered_steps, StopPipeline


PIPELINE_CONFIG_SCHEMA = Schema({
    'type': Or('queue', 'generic'),
    'steps': list
})


class Context(dict):
    """context object"""


def run_pipeline(config):
    """
    run pipeline. type:queue pipelines are running until stop is signaled, all others are run only once
    """

    try:
        if config['type'] == 'queue':
            while True:
                run_generic_pipeline(config)
        else:
            run_generic_pipeline(config)
    except StopPipeline:
        return


def run_generic_pipeline(config):
    """run generic/simple pipeline"""

    current_app.logger.debug(f'run pipeline: {config}')
    ctx = Context()
    for step_config in config['steps']:
        current_app.logger.debug(f'run step: {step_config}')
        args = deepcopy(step_config)
        step = args.pop('step')
        registered_steps[step](ctx, **args)


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
