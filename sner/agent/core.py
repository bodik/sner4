# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent
"""

import copy
import json
import logging
import logging.config
import os
import shutil
import signal
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from base64 import b64encode
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

import marshmallow
import requests

from sner.server.api.schema import JobAssignmentSchema
from sner.lib import load_yaml, TerminateContextMixin
from sner.agent.modules import load_agent_plugins, REGISTERED_MODULES
from sner.version import __version__


LOGGER_NAME = 'sner.agent'
DEFAULT_CONFIG = {
    'SERVER': 'http://localhost:18000',
    'APIKEY': None,
    'QUEUE': None,
    'CAPS': None,
    'BACKOFF_TIME': 5.0,
    'NET_TIMEOUT': 300,
    'ONESHOT': False
}


def configure_logging():
    """configure logging"""

    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': f'{LOGGER_NAME} %(levelname)s %(message)s',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'simple'
            }
        },
        'loggers': {
            LOGGER_NAME: {
                'level': 'INFO',
                'handlers': ['console']
            }
        }
    })


def config_from_yaml(filename):
    """pull config variables from config file"""

    return {k.upper(): v for k, v in load_yaml(filename).get('agent', {}).items()}


def config_from_args(args):
    """pull config variables from parsed args/generic object"""

    config = {}
    for item in ['server', 'apikey', 'queue', 'caps', 'oneshot']:
        if getattr(args, item) is not None:
            config[item.upper()] = getattr(args, item)
    return config


def zipdir(path, zipto):
    """pack directory to in zipfile"""

    with open(zipto, 'wb', 0o600) as output_file:
        with ZipFile(output_file, 'w', ZIP_DEFLATED) as output_zip:
            for root, _dirs, files in os.walk(path):
                for fname in files:
                    filepath = os.path.join(root, fname)
                    arcname = os.path.join(*(filepath.split(os.path.sep)[1:]))
                    output_zip.write(filepath, arcname)


class AgentBase(ABC, TerminateContextMixin):
    """base agent impl containing main (sub)process handling code"""

    def __init__(self):
        self.log = logging.getLogger(LOGGER_NAME)
        self.module_instance = None
        self.original_signal_handlers = {}
        self.loop = None

        load_agent_plugins()

    @abstractmethod
    def run(self, **kwargs):
        """abstract run method; must be implemented by specific agent"""

    def terminate(self, signum=None, frame=None):  # pragma: no cover  pylint: disable=unused-argument  ; running over multiprocessing
        """terminate at once"""

        self.log.info('terminate')
        self.loop = False
        if self.module_instance:
            self.module_instance.terminate()

    def process_assignment(self, assignment):
        """process assignment"""

        jobdir = assignment['id']
        oldcwd = os.getcwd()
        os.makedirs(jobdir, mode=0o700)
        os.chdir(jobdir)

        try:
            self.module_instance = REGISTERED_MODULES[assignment['config']['module']]()
            retval = self.module_instance.run(assignment)
        except Exception as exc:  # pylint: disable=broad-except ; modules can raise variety of exceptions, but agent must continue
            self.log.exception(exc)
            retval = 1
        finally:
            self.module_instance = None

        os.chdir(oldcwd)
        zipdir(jobdir, f'{jobdir}.zip')
        shutil.rmtree(jobdir)

        self.log.info('process_assignment finished, retval=%d', retval)
        return retval


class ServerableAgent(AgentBase):  # pylint: disable=too-many-instance-attributes
    """agent to fetch and execute assignments from central job server"""

    def __init__(self, config):
        super().__init__()

        self.server = config['SERVER']
        self.apikey = config['APIKEY']
        self.queue = config['QUEUE']
        self.caps = config['CAPS']
        self.backoff_time = config['BACKOFF_TIME']
        self.net_timeout = config['NET_TIMEOUT']
        self.oneshot = config['ONESHOT']

        self.loop = True
        self.get_assignment_url = f'{self.server}/api/v2/scheduler/job/assign'
        self.upload_output_url = f'{self.server}/api/v2/scheduler/job/output'

        self.get_assignment_params = {}
        if self.queue:
            self.get_assignment_params['queue'] = self.queue
        if self.caps:
            self.get_assignment_params['caps'] = self.caps

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

    def call_api(self, url, data):
        """call api"""

        return requests.post(url, json=data, headers={'X-API-KEY': self.apikey}, timeout=self.net_timeout)

    def get_assignment(self):
        """get assignment from server"""

        assignment = None
        while self.loop and not assignment:
            try:
                response = self.call_api(self.get_assignment_url, self.get_assignment_params)
                response.raise_for_status()
                assignment = response.json()
                if not assignment:  # response-nowork
                    self.log.debug('get_assignment response-nowork')
                    if self.oneshot:  # pylint: disable=no-else-break  ; improves readability for following pragma
                        break
                    else:  # pragma: no cover ; running over multiprocessing
                        sleep(self.backoff_time)
                        continue
                JobAssignmentSchema().load(assignment)
            except (requests.exceptions.RequestException, json.decoder.JSONDecodeError, marshmallow.ValidationError) as exc:
                assignment = None
                self.log.error('get_assignment error, %s', exc)
                if self.oneshot:
                    return assignment, 1
                sleep(self.backoff_time)

        self.log.info('get_assignment success, %s', assignment)
        return assignment, 0

    def upload_output(self, output):
        """upload assignment output to the server"""

        uploaded = False
        while not uploaded:
            try:
                response = self.call_api(self.upload_output_url, output)
                response.raise_for_status()
                uploaded = True
            except requests.exceptions.RequestException as exc:
                self.log.error('upload_output error, %s', exc)
                sleep(self.backoff_time)
        self.log.info('upload_output success, %s', output['id'])

    def run(self, **kwargs):
        """fetch, process and upload output for assignment given by server"""

        retval = 0
        with self.terminate_context(), self.shutdown_context():
            while self.loop:
                assignment, retval = self.get_assignment()

                if assignment:
                    retval = self.process_assignment(assignment)

                    assignment_output_file = f'{assignment["id"]}.zip'
                    output = {
                        'id': assignment['id'],
                        'retval': retval,
                        'output': b64encode(Path(assignment_output_file).read_bytes()).decode('utf-8')
                    }
                    self.upload_output(output)
                    os.remove(assignment_output_file)

                if self.oneshot:
                    self.loop = False

        return retval


class AssignableAgent(AgentBase):
    """agent to execute assignments supplied from command line"""

    def run(self, **kwargs):
        """process user supplied assignment"""

        assignment = {'id': str(uuid4()), **json.loads(kwargs['assignment'])}
        JobAssignmentSchema().load(assignment)

        with self.terminate_context():
            retval = self.process_assignment(assignment)

        return retval


def main(argv=None):
    """sner agent main"""

    configure_logging()
    logger = logging.getLogger(LOGGER_NAME)

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='show debug output')
    parser.add_argument('--version', action='store_true', help='print version and exit')

    parser.add_argument('--shutdown', type=int, help='request gracefull shutdown of the agent specified by PID')
    parser.add_argument('--terminate', type=int, help='request immediate termination of the agent specified by PID')

    parser.add_argument('--assignment', help='manually specified assignment; mostly for debug purposses')

    parser.add_argument('--config', default='/etc/sner.yaml', help='agent config')
    parser.add_argument('--server', help='server uri')
    parser.add_argument('--apikey', help='server apikey')
    parser.add_argument('--queue', help='specific queue selector')
    parser.add_argument('--caps', nargs='+', help='agent capabilities tags')
    parser.add_argument('--oneshot', action='store_true', help='process single assignment and exit')

    args = parser.parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.debug(args)

    # agent process management helpers
    if args.version:
        print(f'sner {__version__}')
        return 0
    if args.shutdown:
        return os.kill(args.shutdown, signal.SIGUSR1)
    if args.terminate:
        return os.kill(args.terminate, signal.SIGTERM)

    # agent with custom assignment
    if args.assignment:
        return AssignableAgent().run(assignment=args.assignment)

    # standard agent
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(config_from_yaml(args.config))
    config.update(config_from_args(args))
    return ServerableAgent(config).run()
