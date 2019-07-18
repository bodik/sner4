# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers
"""

registered_parsers = {}  # pylint: disable=invalid-name


def register_parser(name):
    """register parser class to registry"""

    def register_parser_real(cls):
        if cls not in registered_parsers:
            registered_parsers[name] = cls
        return cls
    return register_parser_real


import sner.server.parser.nmap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.nessus  # noqa: E402,F401  pylint: disable=wrong-import-position
