# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent screenshot web
"""

import json
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from time import sleep
from uuid import uuid4

from schema import Schema

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    screenshot_web agent

    ## target specification
    target = *(service-target SP) url
    """

    CONFIG_SCHEMA = Schema({
        'module': 'screenshot_web',
        'delay': int,
        'geometry': str
    })

    def __init__(self):
        super().__init__()
        self.loop = False

    # pylint: disable=duplicate-code
    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        results = {}

        for item in assignment['targets']:
            url = item.split(' ', maxsplit=1)[-1]
            filebase = str(uuid4())
            screenshot_path = Path(f'{filebase}.png')
            profile_dir = Path(f'{filebase}.profile')
            profile_dir.mkdir()

            self._execute(
                [
                    'timeout', '60',
                    'firefox', '--headless', '--profile', profile_dir,
                    '--screenshot', screenshot_path.absolute(), '--window-size', assignment['config']['geometry'],
                    url
                ],
                f'{filebase}.output'
            )
            rmtree(f'{profile_dir}')
            results[str(screenshot_path)] = {'target': item, 'timestamp': datetime.now().isoformat()}
            Path('results.json').write_text(json.dumps(results), encoding='utf-8')

            sleep(assignment['config']['delay'])

            if not self.loop:  # pragma: no cover  ; not tested
                break

        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
