"""sner agent execution modules"""

import json
import logging
import os
import shlex
import signal
import subprocess


registered_modules = {}  # pylint: disable=invalid-name


def register_module(name):
    """register module class to registry"""

    def register_module_real(cls):
        if cls not in registered_modules:
            registered_modules[name] = cls
        return cls
    return register_module_real


class Base():
    """simple dummy agent module"""

    def __init__(self):
        self.log = logging.getLogger('sner.agent.module.%s' % __class__)
        self.process = None

    def run(self, assignment):  # pylint: disable=no-self-use
        """run the agent"""

        with open('assignment.json', 'w+') as ftmp:
            ftmp.write(json.dumps(assignment))
        return 0

    def execute(self, cmd, output_file='output'):
        """execute command and capture output"""

        with open(output_file, 'w') as output_fd:
            self.process = subprocess.Popen(shlex.split(cmd), stdin=subprocess.DEVNULL, stdout=output_fd, stderr=subprocess.STDOUT)
            retval = self.process.wait()
            self.process = None
        return retval

    def terminate(self):  # pragma: no cover  ; running over multiprocessing
        """terminate executed command"""

        if self.process and (self.process.poll() is None):
            try:
                os.kill(self.process.pid, signal.SIGTERM)
            except OSError as e:
                self.log.error(e)


@register_module('dummy')
class Dummy(Base):
    """testing agent impl"""
    pass


@register_module('nmap')
class Nmap(Base):
    """nmap wrapper"""

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        with open('targets', 'w') as ftmp:
            ftmp.write('\n'.join(assignment['targets']))
        return self.execute('nmap -iL targets -oA output %s' % assignment['params'])
