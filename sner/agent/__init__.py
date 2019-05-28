#!/usr/bin/env python
"""sner agent"""

import abc
import json
import logging
import os
import shutil
import signal
import sys
from argparse import ArgumentParser
from base64 import b64encode
from contextlib import contextmanager
from time import sleep
from zipfile import ZipFile, ZIP_DEFLATED

import jsonschema
import requests

import sner.agent.protocol
from sner.agent.modules import registered_modules


logger = logging.getLogger('sner.agent')  # pylint: disable=invalid-name
logging.basicConfig(stream=sys.stdout, format='%(levelname)s %(message)s')
logger.setLevel(logging.INFO)


def zipdir(path, zipto):
    """pack directory to in zipfile"""

    with open(zipto, 'wb', 0o600) as output_file:
        with ZipFile(output_file, 'w', ZIP_DEFLATED) as output_zip:
            for root, _dirs, files in os.walk(path):
                for fname in files:
                    filepath = os.path.join(root, fname)
                    arcname = os.path.join(*(filepath.split(os.path.sep)[1:]))
                    output_zip.write(filepath, arcname)


class BaseAgent():
    """base agent impl containing main (sub)process handling code"""

    def __init__(self):
        self.log = logging.getLogger('sner.agent')
        self.module_instance = None
        self.original_signal_handlers = {}
        self.loop = None

    @abc.abstractmethod
    def run(self, **kwargs):
        """abstract run method; must be implemented by specific agent"""

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running as signal handler
        """terminate at once"""

        self.log.info('terminate')
        self.loop = False
        if self.module_instance:
            self.module_instance.terminate()

    @contextmanager
    def terminate_context(self):
        """terminate context manager; should restore handlers despite underlying code exceptions"""

        self.original_signal_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, self.terminate)
        self.original_signal_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, self.terminate)
        try:
            yield
        finally:
            signal.signal(signal.SIGINT, self.original_signal_handlers[signal.SIGINT])
            signal.signal(signal.SIGTERM, self.original_signal_handlers[signal.SIGTERM])

    def process_assignment(self, assignment):
        """process assignment"""

        jobdir = assignment['id']
        oldcwd = os.getcwd()
        os.makedirs(jobdir, mode=0o700)
        os.chdir(jobdir)

        with self.terminate_context():
            try:
                self.module_instance = registered_modules[assignment['module']]()
                retval = self.module_instance.run(assignment)
            except Exception as e:  # pylint: disable=broad-except ; modules can raise variety of exceptions, but agent must continue
                self.log.exception(e)
                retval = 1
            finally:
                self.module_instance = None

        os.chdir(oldcwd)
        zipdir(jobdir, '%s.zip' % jobdir)
        shutil.rmtree(jobdir)

        return retval


class ServerableAgent(BaseAgent):
    """agent to fetch and execute assignments from central job server"""

    BACKOFF_TIME = 5

    def __init__(self, server, queue, oneshot=False):
        super().__init__()

        self.server = server
        self.queue = queue
        self.oneshot = oneshot

        self.loop = True
        self.get_assignment_url = '%s/scheduler/job/assign%s' % (self.server, '/%s' % self.queue if self.queue else '')
        self.upload_output_url = '%s/scheduler/job/output' % self.server

    def shutdown(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; runing as signal handler
        """wait for current assignment to finish"""

        self.log.info('shutdown')
        self.loop = False

    @contextmanager
    def shutdown_context(self):
        """shutdown context manager; should restore handlers despite underlying code exceptions"""

        self.original_signal_handlers[signal.SIGUSR1] = signal.signal(signal.SIGUSR1, self.shutdown)
        try:
            yield
        finally:
            signal.signal(signal.SIGUSR1, self.original_signal_handlers[signal.SIGUSR1])

    def get_assignment(self):
        """get assignment from server"""

        assignment = None
        while self.loop and not assignment:
            try:
                assignment = requests.get(self.get_assignment_url, timeout=10).json()
                if not assignment:  # response-nowork
                    self.log.debug('get_assignment response-nowork')
                    sleep(self.BACKOFF_TIME)
                    continue
                jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)
                self.log.debug('got assignment: %s', assignment)
            except (requests.exceptions.RequestException, json.decoder.JSONDecodeError, jsonschema.exceptions.ValidationError) as e:
                assignment = None
                self.log.warning('get_assignment error: %s', e)
                sleep(self.BACKOFF_TIME)

        return assignment

    def upload_output(self, output):
        """upload assignment output to the server"""

        uploaded = False
        while not uploaded:
            try:
                response = requests.post(self.upload_output_url, json=output, timeout=10)
                response.raise_for_status()
                uploaded = True
            except requests.exceptions.RequestException as e:
                self.log.warning('upload_output error: %s', e)
                sleep(self.BACKOFF_TIME)

    def run(self, **kwargs):
        """fetch, process and upload output for assignment given by server"""

        retval = 0
        with self.shutdown_context():
            while self.loop:
                assignment = self.get_assignment()

                if assignment:
                    retval = self.process_assignment(assignment)
                    self.log.debug('processed, retval=%d', retval)

                    assignment_output_file = '%s.zip' % assignment['id']
                    with open(assignment_output_file, 'rb') as ftmp:
                        output = {'id': assignment['id'], 'retval': retval, 'output': b64encode(ftmp.read()).decode('utf-8')}
                    self.upload_output(output)
                    os.remove(assignment_output_file)

                if self.oneshot:
                    self.loop = False

        return retval


class AssignableAgent(BaseAgent):
    """agent to execute assignments supplied from command line"""

    def run(self, **kwargs):
        """process user supplied assignment"""

        assignment = {'id': 'output'}
        assignment.update(json.loads(kwargs['input_a']))
        jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)

        retval = self.process_assignment(assignment)
        self.log.debug('processed, retval=%d', retval)
        return retval


def main(argv=None):
    """sner agent main"""

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='show debug output')
    parser.add_argument('--server', default='http://localhost:18000', help='server uri')
    parser.add_argument('--queue', help='select specific queue to work on')
    parser.add_argument('--oneshot', action='store_true', help='do not loop for assignments')

    parser.add_argument('--assignment', help='manually specified assignment; mostly for debug purposses')

    parser.add_argument('--shutdown', type=int, help='request gracefull shutdown of the agent specified by PID')
    parser.add_argument('--terminate', type=int, help='request immediate termination of the agent specified by PID')

    args = parser.parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.debug(args)

    # agent process management helpers
    if args.shutdown:
        return os.kill(args.shutdown, signal.SIGUSR1)
    if args.terminate:
        return os.kill(args.terminate, signal.SIGTERM)

    # agent with custom assignment
    if args.assignment:
        return AssignableAgent().run(input_a=args.assignment)

    # standard agent
    return ServerableAgent(args.server, args.queue, args.oneshot).run()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
