# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core
"""

import signal
from contextlib import contextmanager
from time import sleep

from flask import current_app

from sner.server.planner.pipelines import run_queue_pipeline, run_standalone_pipeline


class Planner:
    """planner"""

    LOOPSLEEP = 1

    def __init__(self, oneshot=False):
        self.log = current_app.logger.getChild('sner.server.planner')
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
                        if pipeline['type'] == 'queue':
                            run_queue_pipeline(pipeline)
                        elif pipeline['type'] == 'standalone':
                            run_standalone_pipeline(pipeline)
                        else:
                            raise RuntimeError(f'unsupported pipeline {config}')
                    except Exception as e:  # pylint: disable=broad-except  ; any exception can be raised during pipeline processing
                        current_app.logger.error(f'pipeline failed, {pipeline}, {repr(e)}', exc_info=True)

                if self.oneshot:
                    self.loop = False
                else:  # pragma: no cover ; running over multiprocessing
                    # support for long loops, but allow fast shutdown
                    for _ in range(self.LOOPSLEEP):
                        if self.loop:
                            sleep(1)
