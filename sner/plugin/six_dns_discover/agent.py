# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner agent ipv6 (via ipv4 enum ptr) dns discovery module
"""

import json
from pathlib import Path
from socket import AF_INET6, getaddrinfo, gethostbyaddr
from time import sleep

from schema import Schema

from sner.agent.modules import ModuleBase


class AgentModule(ModuleBase):
    """
    dns based ipv6 from ipv4 address discover

    ## target specification
    target = IPv4Address
    """

    CONFIG_SCHEMA = Schema({
        'module': 'six_dns_discover',
        'delay': int
    })

    def __init__(self):
        super().__init__()
        self.loop = True

    # pylint: disable=duplicate-code
    def run(self, assignment):
        """run the agent"""

        super().run(assignment)

        result = {}
        for addr in assignment['targets']:
            try:
                (hostname, _, _) = gethostbyaddr(addr)
                resolved_addrs = getaddrinfo(hostname, None, AF_INET6)
                for _, _, _, _, sockaddr in resolved_addrs:
                    result[sockaddr[0]] = (hostname, addr)
            except OSError:
                continue
            finally:
                sleep(assignment['config']['delay'])

            if not self.loop:  # pragma: no cover  ; not tested
                break

        Path('output.json').write_text(json.dumps(result), encoding='utf-8')
        return 0

    def terminate(self):  # pragma: no cover  ; not tested / running over multiprocessing
        """terminate scanner if running"""

        self.loop = False
