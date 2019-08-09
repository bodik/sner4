# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent execution modules
"""

import json
import logging
import os
import re
import shlex
import signal
import subprocess
from abc import ABC, abstractmethod


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
    Base class for agent modules. For ABNF target specifications literals not
    explicitly specified here see 'RFC 3986 Appendix A: Collected ABNF for URI'
    (https://tools.ietf.org/html/rfc3986#appendix-A)
    """

    def __init__(self):
        self.log = logging.getLogger('sner.agent.module.%s' % __class__)
        self.process = None

    @abstractmethod
    def run(self, assignment):  # pylint: disable=no-self-use
        """run module for assignment"""

        with open('assignment.json', 'w+') as ftmp:
            ftmp.write(json.dumps(assignment))

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


@register_module('dummy')
class Dummy(ModuleBase):
    """
    testing module implementation

    ## target specification

    target = 1*CHAR
    """

    def run(self, assignment):
        """simply write assignment and return"""
        super().run(assignment)
        return 0

    def terminate(self):
        """nothing to be done for dummy terminate"""


@register_module('nmap')
class Nmap(ModuleBase):
    """
    nmap module

    ## target specification
    note: MUST NOT mix ipv4 and ipv6 targets

    target = IPv4address / IPv6address / reg-name
    """

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        with open('targets', 'w') as ftmp:
            ftmp.write('\n'.join(assignment['targets']))
        return self._execute('nmap %s -oA output -iL targets' % assignment['params'])

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""
        self._terminate()


@register_module('manymap')
class Manymap(ModuleBase):
    """
    internet endpoints nmap-based scanner

    ## target specification

    proto    = "tcp" / "udp"
    hostspec = IPv4address / "[" IPv6address "]" / reg-name
    port     = 1*DIGIT
    target   = proto "://" hostspec ":" port
    """

    TARGET_RE = r'^(?P<proto>tcp|udp)://(?P<host>[0-9\.]{7,15}|\[[0-9a-fA-F:]{3,45}\]|[0-9a-zA-Z\.\-]{1,256}):(?P<port>[0-9]+)$'

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        ret = 0
        super().run(assignment)

        for idx, target in enumerate(assignment['targets']):
            mtmp = re.match(self.TARGET_RE, target)
            if mtmp:
                cmd = ['nmap'] + shlex.split(assignment['params']) \
                    + ['-oA', 'output-%d' % idx, '-p', '%s:%s' % (mtmp.group('proto')[0].upper(), mtmp.group('port'))]
                host = mtmp.group('host')
                if (host[0] == '[') and (host[-1] == ']'):
                    cmd += ['-6', host[1:-1]]
                else:
                    cmd.append(host)
                ret |= self._execute(cmd, 'output-%d' % idx)
            else:
                self.log.warning('invalid target: %s', target)
            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
