# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
Rate-limit heatmap for scheduler
"""

import json
from collections import defaultdict
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from pathlib import Path

from flask import current_app


class Heatmap:
    """rate-limiting heatmap implementation"""

    def __init__(self):
        self.path = Path(f'{current_app.config["SNER_VAR"]}/heatmap.json')
        self.hot_level = current_app.config['SNER_HEATMAP_HOT_LEVEL']
        self.map = defaultdict(int, json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {})

    def put(self, value):
        """warm value"""

        self.map[value] += 1

    def pop(self, value):
        """cool value"""

        self.map[value] -= 1
        if self.map[value] == 0:
            self.map.pop(value)

    def is_hot(self, value):
        """check if value is hot (over limit)"""

        return self.map[value] >= self.hot_level

    def save(self):
        """save heatmap state"""

        self.path.write_text(json.dumps(self.map), encoding='utf-8')

    @staticmethod
    def hashval(value):
        """computes rate-limit heatmap hash value"""

        try:
            addr = ip_address(value)
            if isinstance(addr, IPv4Address):
                return str(ip_network(f'{ip_address(value)}/24', strict=False))
            if isinstance(addr, IPv6Address):
                return str(ip_network(f'{ip_address(value)}/48', strict=False))
        except ValueError:
            pass

        return value
