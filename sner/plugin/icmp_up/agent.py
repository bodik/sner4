# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent icmp up module
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def ping_target(self, target, args):
        """ping the target"""
        if '-c' not in args:
            args += ['-c', '1']

        cmd = ['ping'] + args + [target]

        return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) == 0

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)

        with ThreadPoolExecutor() as executor:
            futures = {}

            for target in assignment['targets']:
                futures[executor.submit(self.ping_target, target, shlex.split(assignment['config']['args']))] = target

            for future in as_completed(futures):
                target = futures[future]

                with open('output', 'a', encoding='utf-8') as output_file:
                    if future.result():
                        output_file.write(f'{target} UP\n')
                    else:
                        output_file.write(f'{target} DOWN\n')

                if not self.loop:  # pragma: no cover  ; not tested
                    break

        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
