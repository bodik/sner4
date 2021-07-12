#!/usr/bin/env python3
"""
add tags to hosts by list of addresses
"""

from argparse import ArgumentParser
from pathlib import Path

from sner.server.app import create_app
from sner.server.extensions import db
from sner.server.storage.models import Host


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('tag')
    args = parser.parse_args()

    addrs = Path(args.filename).read_text().splitlines()

    with create_app().app_context():
        for host in Host.query.all():
            if host.address in addrs:
                print(host)
                host.tags = host.tags + [args.tag]

        db.session.commit()


if __name__ == '__main__':
    main()
