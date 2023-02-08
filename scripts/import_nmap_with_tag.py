#/usr/bin/env python3
"""import and tag open services from nmap jobs"""

import logging
from argparse import ArgumentParser
from pathlib import Path

from sner.plugin.nmap.parser import ParserModule as NmapParserModule
from sner.server.app import create_app
from sner.server.extensions import db
from sner.server.storage.core import db_service


logger = logging.getLogger()  # pylint: disable=invalid-name
logger.addHandler(logging.StreamHandler())


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('inputfile', nargs='+')
    args = parser.parse_args()

    with create_app().app_context():
        for inputfile in args.inputfile:
            print(inputfile)
            pidb = NmapParserModule.parse_path(inputfile)
            for iservice in pidb.services:
                if 'open' in iservice.state:
                    print(iservice)
                    dbitem = db_service(pidb.hosts[iservice.host_iid].address, iservice.proto, iservice.port)
                    if not dbitem:
                        breakpoint()
                    else:
                        dbitem.tags = dbitem.tags + ['public']

        db.session.commit()


if __name__ == '__main__':
    main()
