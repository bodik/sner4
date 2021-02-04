# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent dummy module
"""

from schema import Schema

from sner.agent.modules import ModuleBase, register_module


@register_module('dummy')
class Dummy(ModuleBase):
    """
    testing module implementation

    ## target specification
    target = simple-target
    """

    CONFIG_SCHEMA = Schema({
        'module': 'dummy',
        'args': str
    })

    def run(self, assignment):
        """simply write assignment and return"""

        super().run(assignment)
        return 0

    def terminate(self):
        """nothing to be done for dummy terminate"""
