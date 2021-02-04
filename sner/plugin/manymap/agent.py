# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent manymap module
"""

import shlex
from time import sleep

from schema import Schema

from sner.agent.modules import ModuleBase, register_module


@register_module('manymap')
class Manymap(ModuleBase):
    """
    internet endpoints nmap-based scanner

    ## target specification
    target = service-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'manymap',
        'args': str,
        'delay': int,
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        ret = 0

        for idx, _, proto, host, port in self.enumerate_service_targets(assignment['targets']):
            output_args = ['-oA', f'output-{idx}', '--reason']
            target_args = ['-p', f'{proto[0].upper()}:{port}']
            if (host[0] == '[') and (host[-1] == ']'):
                target_args += ['-6', host[1:-1]]
            else:
                target_args += [host]

            cmd = ['nmap'] + shlex.split(assignment['config']['args']) + output_args + target_args
            ret |= self._execute(cmd, f'output-{idx}')
            sleep(assignment['config']['delay'])

            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
