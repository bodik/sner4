#!/usr/bin/env python3
"""
reporting helper, will duplicate vuln to the specified host and service

usage: PYTHONPATH='.' python3 scripts/copy_vuln.py VULN_ID ADDRESS [PROTO PORT]
"""

from argparse import ArgumentParser

from sner.server.app import create_app
from sner.server.extensions import db
from sner.server.storage.models import Host, Service, Vuln


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('vuln_id')
    parser.add_argument('target_address')
    parser.add_argument('target_proto', nargs='?')
    parser.add_argument('target_port', nargs='?')
    args = parser.parse_args()

    with create_app().app_context():
        vuln = Vuln.query.get(args.vuln_id)
        host = Host.query.filter(Host.address == args.target_address).one()
        service = None
        if args.target_port:
            service = Service.query.filter(Service.host == host, Service.proto == args.target_proto, Service.port == args.target_port).one()

        newvuln = Vuln()
        for column in Vuln.__table__.columns:
            if column.primary_key or column.foregin_keys:
                continue
            if hasattr(newvuln, column.name):
                setattr(newvuln, column.name, getattr(vuln, column.name))

        newvuln.host_id = host.id
        newvuln.service_id = service.id if service else None

        db.session.add(newvuln)
        db.session.commit()
        db.session.refresh(newvuln)
        print(newvuln)


if __name__ == '__main__':
    main()
