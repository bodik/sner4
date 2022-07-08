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
from importlib import import_module
from pathlib import Path

from schema import Schema

import sner.plugin


REGISTERED_MODULES = {}
SERVICE_TARGET_REGEXP = r'^(?P<proto>tcp|udp)://(?P<host>[0-9\.]{7,15}|[0-9a-zA-Z\.\-]{1,256}|\[[0-9a-fA-F:]{3,45}\]|\[[0-9a-zA-Z\.\-]{1,256}\]):(?P<port>[0-9]+)$'  # noqa: 501  pylint: disable=line-too-long


def load_agent_plugins():
    """load all agent plugins/modules"""

    for plugin_path in Path(sner.plugin.__file__).parent.glob('*/agent.py'):
        plugin_name = plugin_path.parent.name
        module = import_module(f'sner.plugin.{plugin_name}.agent')
        REGISTERED_MODULES[plugin_name] = getattr(module, 'AgentModule')


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
    def run(self, assignment):
        """run module for assignment"""

        Path('assignment.json').write_text(json.dumps(assignment), encoding='utf-8')
        self.CONFIG_SCHEMA.validate(assignment['config'])

    @abstractmethod
    def terminate(self):
        """terminate method; should terminate module immediatelly"""

    def _terminate(self):  # pragma: no cover  ; running over multiprocessing
        """terminate executed command"""

        if self.process and (self.process.poll() is None):
            try:
                os.kill(self.process.pid, signal.SIGTERM)
            except OSError as exc:
                self.log.error(exc)

    def _execute(self, cmd, output_file='output'):
        """execute command and capture output"""

        cmdarg = shlex.split(cmd) if isinstance(cmd, str) else cmd
        with open(output_file, 'w', encoding='utf-8') as output_fd:
            self.process = subprocess.Popen(cmdarg, stdin=subprocess.DEVNULL, stdout=output_fd, stderr=subprocess.STDOUT)  # noqa: E501  pylint: disable=consider-using-with
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
