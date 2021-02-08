# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage commands
"""

import json
import os
import sys

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy_filters import apply_filters

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.parser import REGISTERED_PARSERS
from sner.server.sqlafilter import FILTER_PARSER
from sner.server.storage.core import import_parsed, vuln_export, vuln_report
from sner.server.storage.models import Host, Service


@click.group(name='storage', help='sner.server storage management')
def command():
    """storage commands container"""


@command.command(name='import', help='import data from files')
@with_appcontext
@click.argument('parser')
@click.argument('path', nargs=-1)
def storage_import(path, parser):
    """import data"""

    if parser not in REGISTERED_PARSERS:
        current_app.logger.error('no such parser')
        sys.exit(1)

    parser_impl = REGISTERED_PARSERS[parser]
    for item in path:
        if not os.path.isfile(item):
            current_app.logger.error(f'invalid path "{item}"')
            sys.exit(1)
        import_parsed(parser_impl.parse_path(item))

    sys.exit(0)


@command.command(name='flush', help='flush all objects from storage')
@with_appcontext
def storage_flush():
    """flush all objects from storage"""

    db.session.query(Host).delete()
    db.session.commit()


@command.command(name='report', help='generate vuln report')
@with_appcontext
def storage_report():
    """generate vuln report"""
    print(vuln_report())


@command.command(name='vuln-export', help='export vulnerabilities')
@with_appcontext
def storage_vuln_export():
    """export vulnerabilities"""
    print(vuln_export())


@command.command(name='service-list', help='service (filtered) listing')
@with_appcontext
@click.option('--filter', help='filter query')
@click.option('--hostnames', is_flag=True, help='show host.hostname')
@click.option('--short', is_flag=True, help='show service.host.address/hostname')
@click.option('--simple', is_flag=True, help='show "service.host.addresss service.port"')
@click.option('--long', is_flag=True, help='show service extended info')
def storage_service_list(**kwargs):
    """service listing; used to feed manymap queues from storage data"""

    def get_host(svc, hostnames=False):
        """return address or hostname"""

        if hostnames and svc.host.hostname:
            return svc.host.hostname
        return format_host_address(svc.host.address)

    def get_data(svc):
        """return common data as dict"""
        return {'proto': svc.proto, 'port': svc.port, 'name': svc.name, 'state': svc.state, 'info': json.dumps(svc.info)}

    if kwargs['long'] and kwargs['short']:
        current_app.logger.error('--short and --long are mutualy exclusive options')
        sys.exit(1)

    query = Service.query
    if kwargs['filter']:
        query = apply_filters(query, FILTER_PARSER.parse(kwargs['filter']), do_auto_join=False)

    fmt = '{proto}://{host}:{port}'
    if kwargs['short']:
        fmt = '{host}'
    elif kwargs['simple']:
        fmt = '{host} {port}'
    elif kwargs['long']:
        fmt = '{proto}://{host}:{port} {name} {state} {info}'

    for tmp in query.all():
        print(fmt.format(**get_data(tmp), host=get_host(tmp, kwargs['hostnames'])))
