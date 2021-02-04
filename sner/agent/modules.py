# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent execution module base

## Target specification ABNFs

For ABNF target specifications literals not explicitly specified here see
'RFC 3986 Appendix A: Collected ABNF for URI' (https://tools.ietf.org/html/rfc3986#appendix-A)

simple-target  = 1*CHAR

host-target    = IPv4address / reg-name / "[" IPv6address "]" / "[" reg-name "]"

proto          = "tcp" / "udp"
port           = 1*DIGIT
service-target = proto "://" host-target ":" port
"""

import json
import logging
import os
import re
import signal
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from schema import Schema

SERVICE_TARGET_REGEXP = r'^(?P<proto>tcp|udp)://(?P<host>[0-9\.]{7,15}|[0-9a-zA-Z\.\-]{1,256}|\[[0-9a-fA-F:]{3,45}\]|\[[0-9a-zA-Z\.\-]{1,256}\]):(?P<port>[0-9]+)$'  # noqa: 501  pylint: disable=line-too-long
registered_modules = {}  # pylint: disable=invalid-name


def register_module(name):
    """register module class to registry"""

    def register_module_real(cls):
        if cls not in registered_modules:
            registered_modules[name] = cls
        return cls
    return register_module_real


class ModuleBase(ABC):
    """
    Base class for agent modules.
    """

    CONFIG_SCHEMA = Schema({
        'module': str
    })

    def __init__(self):
        self.log = logging.getLogger(f'sner.agent.module.{self.__class__.__name__}')
        self.process = None

    @abstractmethod
    def run(self, assignment):  # pylint: disable=no-self-use
        """run module for assignment"""

        Path('assignment.json').write_text(json.dumps(assignment))
        self.CONFIG_SCHEMA.validate(assignment['config'])

    @abstractmethod
    def terminate(self):
        """terminate method; should terminate module immediatelly"""

    def _terminate(self):  # pragma: no cover  ; running over multiprocessing
        """terminate executed command"""

        if self.process and (self.process.poll() is None):
            try:
                os.kill(self.process.pid, signal.SIGTERM)
            except OSError as e:
                self.log.error(e)

    def _execute(self, cmd, output_file='output'):
        """execute command and capture output"""

        cmdarg = shlex.split(cmd) if isinstance(cmd, str) else cmd
        with open(output_file, 'w') as output_fd:
            self.process = subprocess.Popen(cmdarg, stdin=subprocess.DEVNULL, stdout=output_fd, stderr=subprocess.STDOUT)
            retval = self.process.wait()
            self.process = None
        return retval

    def enumerate_service_targets(self, targets):
        """
        parse list of service targets, discards invalid values

        :return: tuple of parsed target data
        :rtype: (target index, target, proto, host, port)
        """

        for idx, target in enumerate(targets):
            mtmp = re.match(SERVICE_TARGET_REGEXP, target)
            if mtmp:
                yield idx, target, mtmp.group('proto'), mtmp.group('host'), mtmp.group('port')
            else:
                self.log.warning('invalid service target: %s', target)
