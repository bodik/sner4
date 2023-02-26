# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent testssl module
"""

from time import sleep

from schema import Schema

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    internet endpoints nmap-based scanner

    ## target specification
    target = service-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'testssl',
        'delay': int,
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)

        for idx, target, proto, host, port in self.enumerate_service_targets(assignment['targets']):
            if proto != 'tcp':
                self.log.warning('ignoring non-tcp target %s', target)
                continue

            target_args = ['--jsonfile-pretty', f'output-{idx}.json', f'{host}:{port}']
            cmd = ['testssl.sh', '--quiet', '--full', '--connect-timeout', '5', '--openssl-timeout', '5'] + target_args
            self._execute(cmd, f'output-{idx}')

            sleep(assignment['config']['delay'])
            if not self.loop:  # pragma: no cover  ; not tested
                break

        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
