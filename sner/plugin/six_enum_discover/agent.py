# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent six enum from storage discover
"""

from schema import Schema

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    enumeration based ipv6 discover

    man scan6
    -d DST_ADDRESS, --dst-address DST_ADDRESS
    This  option  specifies the target address prefix/range of the address scan. An IPv6 prefix can be specified in the form 2001:db8::/64,
    or as 2001:db8:a-b:1-10 (where specific address ranges are specified for the two low order 16-bit words). This option must be specified
    for remote address scanning attacks.

    ## target specification
    target   = scan6-dst-address
    """

    CONFIG_SCHEMA = Schema({
        'module': 'six_enum_discover',
        'rate': int,
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    def run(self, assignment):
        """run the agent"""

        super().run(assignment)
        ret = 0

        for idx, target in enumerate(assignment['targets']):
            ret |= self._execute(['scan6', '--rate-limit', f'{assignment["config"]["rate"]}pps', '--dst-address', target], f'output-{idx}.txt')
            if not self.loop:  # pragma: no cover  ; not tested
                break

        return ret

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
        self._terminate()
