# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent jarm module
"""

from time import sleep

from schema import Schema

from sner.agent.modules import ModuleBase, register_module


@register_module('jarm')
class Jarm(ModuleBase):
    """
    jarm fingerprinter

    ## target specification
    target = service-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'jarm',
        'delay': int,
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        ret = 0

        for idx, target, proto, host, port in self.enumerate_service_targets(assignment['targets']):
            if proto != 'tcp':
                self.log.warning('unsupported target (proto): %s', target)
                continue

            target_args = ['-p', port]
            target_args.append(host.replace('[', '').replace(']', ''))

            cmd = ['jarm', '-v'] + target_args
            ret |= self._execute(cmd, f'output-{idx}.out')
            sleep(assignment['config']['delay'])

            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
