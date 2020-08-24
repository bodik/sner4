# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner parsers
"""

from collections import namedtuple


registered_parsers = {}  # pylint: disable=invalid-name

ServiceListItem = namedtuple('ServiceListItem', ['service', 'state'])


def register_parser(name):
    """register parser class to registry"""

    def register_parser_real(cls):
        if cls not in registered_parsers:
            registered_parsers[name] = cls
        return cls
    return register_parser_real


class ParserBase:  # pylint: disable=too-few-public-methods
    """
    parser interface definition

    ABC is not used because it would require too much bload-ware functions and anti pylint duplicate-code hacks
    """

    @staticmethod
    def import_file(path):  # pragma: nocover  ; won't test
        """import file from disk to storage"""
        raise RuntimeError('not implemented')

    @staticmethod
    def service_list(path):  # pragma: nocover  ; won't test
        """parse service list from path"""
        raise RuntimeError('not implemented')

    @staticmethod
    def host_list(path):  # pragma: nocover  ; won't test
        """parse host list from path"""
        raise RuntimeError('not implemented')


import sner.server.parser.manymap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.nessus  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.nmap  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.six_dns_discover  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.parser.six_enum_discover  # noqa: E402,F401  pylint: disable=wrong-import-position
