# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent nuclei module
"""

import shlex
from pathlib import Path
from schema import Schema
from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    nuclei module

    ## target specification
    target = host-target / url
    """

    CONFIG_SCHEMA = Schema({
        'module': 'nuclei',
        'args': str
    })

    def run(self, assignment):
        super().run(assignment)

        Path('targets').write_text('\n'.join(assignment['targets']), encoding='utf-8')

        output_args = ['-nc', '-je', 'output.json', '-se', 'output.sarif.json', '-o', 'output']
        target_args = ['-l', 'targets']

        cmd = ['nuclei'] + target_args + shlex.split(assignment['config']['args']) + output_args

        self._execute(cmd, 'output')

        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self._terminate()
