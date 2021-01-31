# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent
"""

import copy
import json
import logging
import os
import shutil
import signal
import sys
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from base64 import b64encode
from contextlib import contextmanager
from time import sleep
from zipfile import ZipFile, ZIP_DEFLATED

import jsonschema
import requests

import sner.agent.protocol
from sner.lib import get_dotted, load_yaml
from sner.agent.modules import registered_modules
from sner.version import __version__


LOGGER_NAME = 'sner.agent'
DEFAULT_CONFIG = {
    'SERVER': 'http://localhost:18000',
    'APIKEY': None,
    'QUEUE': None
}


def setup_logger():
    """configure logger"""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    logger.addHandler(handler)

    return logger


def config_from_yaml(filename):
    """pull config variables from config file"""

    config_dict = load_yaml(filename)
    config = {
        'SERVER': get_dotted(config_dict, 'agent.server'),
        'APIKEY': get_dotted(config_dict, 'agent.apikey'),
        'QUEUE': get_dotted(config_dict, 'agent.queue')}
    return {k: v for k, v in config.items() if v is not None}


def config_from_args(args):
    """pull config variables from parsed args/generic object"""

    config = {
        'SERVER': args.server,
        'APIKEY': args.apikey,
        'QUEUE': args.queue}
    return {k: v for k, v in config.items() if v is not None}


def apikey_header(apikey):
    """generate apikey header"""
    return {'Authorization': f'Apikey {apikey}'}


def zipdir(path, zipto):
    """pack directory to in zipfile"""

    with open(zipto, 'wb', 0o600) as output_file:
        with ZipFile(output_file, 'w', ZIP_DEFLATED) as output_zip:
            for root, _dirs, files in os.walk(path):
                for fname in files:
                    filepath = os.path.join(root, fname)
                    arcname = os.path.join(*(filepath.split(os.path.sep)[1:]))
                    output_zip.write(filepath, arcname)


class AgentBase(ABC):
    """base agent impl containing main (sub)process handling code"""

    def __init__(self):
        self.log = logging.getLogger(LOGGER_NAME)
        self.module_instance = None
        self.original_signal_handlers = {}
        self.loop = None

    @abstractmethod
    def run(self, **kwargs):
        """abstract run method; must be implemented by specific agent"""

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """terminate at once"""

        self.log.info('terminate')
        self.loop = False
        if self.module_instance:
            self.module_instance.terminate()

    @contextmanager
    def terminate_context(self):
        """terminate context manager; should restore handlers despite of underlying code exceptions"""

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

        try:
            self.module_instance = registered_modules[assignment['config']['module']]()
            retval = self.module_instance.run(assignment)
        except Exception as e:  # pylint: disable=broad-except ; modules can raise variety of exceptions, but agent must continue
            self.log.exception(e)
            retval = 1
        finally:
            self.module_instance = None

        os.chdir(oldcwd)
        zipdir(jobdir, f'{jobdir}.zip')
        shutil.rmtree(jobdir)

        return retval


class ServerableAgent(AgentBase):  # pylint: disable=too-many-instance-attributes
    """agent to fetch and execute assignments from central job server"""

    def __init__(self, server, apikey, queue, oneshot=False, backoff_time=5.0):  # pylint: disable=too-many-arguments
        super().__init__()

        self.server = server
        self.apikey = apikey
        self.queue = queue
        self.oneshot = oneshot
        self.backoff_time = backoff_time

        self.loop = True
        self.get_assignment_url = f'{self.server}/api/v1/scheduler/job/assign'
        self.get_assignment_params = {}
        if self.queue:
            self.get_assignment_params['queue'] = self.queue
        self.upload_output_url = f'{self.server}/api/v1/scheduler/job/output'

    def shutdown(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """wait for current assignment to finish"""

        self.log.info('shutdown')
        self.loop = False

    @contextmanager
    def shutdown_context(self):
        """shutdown context manager; should restore handlers despite of underlying code exceptions"""

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
                response = requests.get(
                    self.get_assignment_url,
                    headers=apikey_header(self.apikey),
                    params=self.get_assignment_params,
                    timeout=10
                )
                response.raise_for_status()
                assignment = response.json()
                if not assignment:  # response-nowork
                    self.log.debug('get_assignment response-nowork')
                    if self.oneshot:  # pylint: disable=no-else-break  ; improves readability for following pragma
                        break
                    else:  # pragma: no cover ; running over multiprocessing
                        sleep(self.backoff_time)
                        continue
                jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)
                self.log.debug('got assignment: %s', assignment)
            except (requests.exceptions.RequestException, json.decoder.JSONDecodeError, jsonschema.exceptions.ValidationError) as e:
                assignment = None
                self.log.warning('get_assignment error: %s', e)
                if self.oneshot:
                    return assignment, 1
                sleep(self.backoff_time)

        return assignment, 0

    def upload_output(self, output):
        """upload assignment output to the server"""

        uploaded = False
        while not uploaded:
            try:
                response = requests.post(self.upload_output_url, json=output, headers=apikey_header(self.apikey), timeout=10)
                response.raise_for_status()
                uploaded = True
            except requests.exceptions.RequestException as e:
                self.log.warning('upload_output error: %s', e)
                sleep(self.backoff_time)

    def run(self, **kwargs):
        """fetch, process and upload output for assignment given by server"""

        retval = 0
        with self.terminate_context(), self.shutdown_context():
            while self.loop:
                assignment, retval = self.get_assignment()

                if assignment:
                    retval = self.process_assignment(assignment)
                    self.log.debug('processed, retval=%d', retval)

                    assignment_output_file = f'{assignment["id"]}.zip'
                    with open(assignment_output_file, 'rb') as ftmp:
                        output = {'id': assignment['id'], 'retval': retval, 'output': b64encode(ftmp.read()).decode('utf-8')}
                    self.upload_output(output)
                    os.remove(assignment_output_file)

                if self.oneshot:
                    self.loop = False

        return retval


class AssignableAgent(AgentBase):
    """agent to execute assignments supplied from command line"""

    def run(self, **kwargs):
        """process user supplied assignment"""

        assignment = {'id': 'output'}
        assignment.update(json.loads(kwargs['input_a']))
        jsonschema.validate(assignment, schema=sner.agent.protocol.assignment)

        with self.terminate_context():
            retval = self.process_assignment(assignment)
            self.log.debug('processed, retval=%d', retval)

        return retval


def main(argv=None):
    """sner agent main"""

    logger = setup_logger()

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='show debug output')
    parser.add_argument('--version', action='store_true', help='print version and exit')

    parser.add_argument('--shutdown', type=int, help='request gracefull shutdown of the agent specified by PID')
    parser.add_argument('--terminate', type=int, help='request immediate termination of the agent specified by PID')

    parser.add_argument('--assignment', help='manually specified assignment; mostly for debug purposses')

    parser.add_argument('--config', default='/etc/sner.yaml', help='agent config')
    parser.add_argument('--server', help='server uri')
    parser.add_argument('--apikey', help='server apikey')
    parser.add_argument('--queue', help='select specific queue to work on')
    parser.add_argument('--oneshot', action='store_true', help='do not loop for assignments')
    parser.add_argument('--backofftime', type=float, default=5.0, help='backoff time for repeating requests; used to speedup tests')

    args = parser.parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.debug(args)

    # agent process management helpers
    if args.version:
        print(f'Sner {__version__}')
        return 0
    if args.shutdown:
        return os.kill(args.shutdown, signal.SIGUSR1)
    if args.terminate:
        return os.kill(args.terminate, signal.SIGTERM)

    # agent with custom assignment
    if args.assignment:
        return AssignableAgent().run(input_a=args.assignment)

    # standard agent
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(config_from_yaml(args.config))
    config.update(config_from_args(args))
    return ServerableAgent(config.get('SERVER'), config.get('APIKEY'), config.get('QUEUE'), args.oneshot, args.backofftime).run()
