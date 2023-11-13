# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent icmp up module
"""

import subprocess
import multiprocessing
import shlex

from schema import Schema

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    icmp up module

    ## target specification
    target = host-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'icmp_up',
        'args': str,
    })

    def __init__(self):
        super().__init__()
        self.loop = True
        self.processes = []

    def ping_target(self, target, args):  # pragma: no cover  ; not tested / running over multiprocessing
        """ping the target"""
        if '-c' not in args:
            args += ['-c', '1']

        cmd = ['ping'] + args + [target]

        return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0

    def process_target(self, target, args):  # pragma: no cover  ; not tested / running over multiprocessing
        """process the target"""
        result = self.ping_target(target, args)

        with open('output', 'a', encoding='utf-8') as output_file:
            if result:
                output_file.write(f'{target} UP\n')
            else:
                output_file.write(f'{target} DOWN\n')

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)

        for target in assignment['targets']:
            process = multiprocessing.Process(target=self.process_target, args=(target, shlex.split(assignment['config']['args'])))
            process.start()
            self.processes.append(process)

            if not self.loop:  # pragma: no cover  ; not tested
                break

        # wait for all processes to finish
        for process in self.processes:
            process.join()

        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False

        # terminate all processes
        for process in self.processes:
            process.kill()

        self._terminate()
