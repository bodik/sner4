# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers
"""

from abc import ABC, abstractmethod


registered_parsers = {}  # pylint: disable=invalid-name


def register_parser(name):
    """register parser class to registry"""

    def register_parser_real(cls):
        if cls not in registered_parsers:
            registered_parsers[name] = cls
        return cls
    return register_parser_real


class ParserBase(ABC):  # pylint: disable=too-few-public-methods
    """parser interface definition"""

    @staticmethod
    @abstractmethod
    def import_file(path):
        """import file from disk to storage"""


import sner.server.parser.manymap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.nessus  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.nmap  # noqa: E402,F401  pylint: disable=wrong-import-position
