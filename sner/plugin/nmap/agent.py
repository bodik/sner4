# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent nmap module
"""

import shlex
from ipaddress import AddressValueError, IPv6Address
from pathlib import Path

from schema import Schema, Optional

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    nmap module

    ## target specification
    target = host-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'nmap',
        'args': str,
        Optional('timing_perhost'): int
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    @staticmethod
    def sort_ipv6_targets(intargets):
        """split v4 and v6 targets"""

        targets, targets6 = [], []

        for target in intargets:
            # brackets enforces target to be ipv6 (mostly for hostnames)
            if (target[0] == '[') and (target[-1] == ']'):
                targets6.append(target[1:-1])
                continue

            # default ipv6 addr detection
            try:
                IPv6Address(target)
                targets6.append(target)
                continue
            except AddressValueError:
                pass

            # all other targets
            targets.append(target)

        return targets, targets6

    def run_scan(self, assignment, targets, targets_file, output_file, extra_args=None):  # pylint: disable=too-many-arguments
        """run scan"""

        Path(targets_file).write_text('\n'.join(targets))

        timing_args = []
        if 'timing_perhost' in assignment['config']:
            output_rate = assignment['config']['timing_perhost'] * len(targets)
            timing_args = [
                '--max-retries', '3',
                '--script-timeout', '10m',
                '--min-hostgroup', str(len(targets)),
                '--min-rate', str(output_rate),
                '--max-rate', str(int(output_rate * 1.05))
            ]

        output_args = ['-oA', output_file, '--reason']
        target_args = ['-iL', targets_file]

        cmd = ['nmap'] + (extra_args or []) + shlex.split(assignment['config']['args']) + timing_args + output_args + target_args
        return self._execute(cmd, output_file)

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        ret = 0

        targets, targets6 = self.sort_ipv6_targets(assignment['targets'])
        if targets and self.loop:
            ret |= self.run_scan(assignment, targets, 'targets', 'output')
        if targets6 and self.loop:
            ret |= self.run_scan(assignment, targets6, 'targets6', 'output6', extra_args=['-6'])
        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
