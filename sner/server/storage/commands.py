# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage commands
"""

import json
import sys
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.parser import REGISTERED_PARSERS
from sner.server.storage.core import StorageManager, vuln_export, vuln_report
from sner.server.storage.models import Host, Service
from sner.server.storage.vulnsearch import sync_vulnsearch
from sner.server.storage.syncstorage import sync_storage
from sner.server.utils import filter_query


@click.group(name='storage', help='sner.server storage management')
def command():
    """storage commands container"""


@command.command(name='import', help='import data from files')
@with_appcontext
@click.option('--dry', is_flag=True, help='do not update database, only print new items')
@click.option('--addtag', multiple=True, help='add tag to all imported objects, can be used several times')
@click.argument('parser')
@click.argument('path', nargs=-1)
def storage_import(path, parser, **kwargs):
    """import data"""

    if parser not in REGISTERED_PARSERS:
        current_app.logger.error('no such parser')
        sys.exit(1)

    parser_impl = REGISTERED_PARSERS[parser]
    for item in path:
        if not Path(item).is_file():
            current_app.logger.warning(f'invalid path "{item}"')
            continue

        try:
            if kwargs.get('dry'):
                StorageManager.import_parsed_dry(parser_impl.parse_path(item))
            else:
                StorageManager.import_parsed(parser_impl.parse_path(item), list(kwargs['addtag']))
        except Exception as exc:  # pylint: disable=broad-except
            current_app.logger.warning(f'failed to parse {item}, {exc}')

    sys.exit(0)


@command.command(name='flush', help='flush all objects from storage')
@with_appcontext
def storage_flush():
    """flush all objects from storage"""

    db.session.query(Host).delete()
    db.session.commit()


@command.command(name='vuln-report', help='generate vulnerabilities report')
@with_appcontext
@click.option('--filter', help='filter query')
@click.option('--group_by_host', is_flag=True, help='generate report per host')
def storage_vuln_report(**kwargs):
    """generate vuln report"""

    print(vuln_report(kwargs.get('filter'), kwargs.get('group_by_host')))


@command.command(name='vuln-export', help='export vulnerabilities')
@with_appcontext
@click.option('--filter', help='filter query')
def storage_vuln_export(**kwargs):
    """export vulnerabilities"""

    print(vuln_export(kwargs.get('filter')))


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

    if not (query := filter_query(Service.query, kwargs.get('filter'))):
        current_app.logger.error('failed to filter query')
        sys.exit(1)

    fmt = '{proto}://{host}:{port}'
    if kwargs['short']:
        fmt = '{host}'
    elif kwargs['simple']:
        fmt = '{host} {port}'
    elif kwargs['long']:
        fmt = '{proto}://{host}:{port} {name} {state} {info}'

    for tmp in query.all():
        print(fmt.format(**get_data(tmp), host=get_host(tmp, kwargs['hostnames'])))


@command.command(name='sync-vulnsearch', help='synchronize vulnsearch elk index')
@with_appcontext
@click.option('--namelen', default=100, help='emited name length')
@click.option('--cvesearch', help='cvesearch base url')
@click.option('--esd', help='elasticsearch url')
@click.option('--tlsauth_key', help='tlsauth key path')
@click.option('--tlsauth_cert', help='tlsauth cert path')
@click.option('--host_filter',  type=click.Path(exists=True), help='path to host filter file')
def storage_sync_vulnsearch(**kwargs):
    """synchronize vulnsearch elk index"""

    cvesearch = kwargs.get('cvesearch') or current_app.config['SNER_VULNSEARCH'].get('cvesearch')
    esd = kwargs.get('esd') or current_app.config['SNER_VULNSEARCH'].get('esd')
    tlsauth_key = kwargs.get('tlsauth_key') or current_app.config['SNER_VULNSEARCH'].get('tlsauth_key')
    tlsauth_cert = kwargs.get('tlsauth_cert') or current_app.config['SNER_VULNSEARCH'].get('tlsauth_cert')
    host_filter = Path(kwargs['host_filter']).read_text(encoding='utf-8').splitlines() if kwargs.get('host_filter') else None

    if not all([cvesearch, esd]):
        current_app.logger.error('configuration required (config or cmdline)')
        sys.exit(1)

    sync_vulnsearch(cvesearch, esd, kwargs.get('namelen'), tlsauth_key, tlsauth_cert, host_filter)


@command.command(name='sync-storage', help='synchronize storage elk index')
@with_appcontext
@click.option('--esd', help='elasticsearch url')
@click.option('--tlsauth_key', help='tlsauth key path')
@click.option('--tlsauth_cert', help='tlsauth cert path')
@click.option('--host_filter',  type=click.Path(exists=True), help='path to host filter file')
def storage_sync_storage(**kwargs):
    """synchronize storage elk index"""

    esd = kwargs.get('esd') or current_app.config['SNER_VULNSEARCH'].get('esd')
    tlsauth_key = kwargs.get('tlsauth_key') or current_app.config['SNER_VULNSEARCH'].get('tlsauth_key')
    tlsauth_cert = kwargs.get('tlsauth_cert') or current_app.config['SNER_VULNSEARCH'].get('tlsauth_cert')
    host_filter = Path(kwargs['host_filter']).read_text(encoding='utf-8').splitlines() if kwargs.get('host_filter') else None

    if not esd:
        current_app.logger.error('configuration required (config or cmdline)')
        sys.exit(1)

    sync_storage(esd, tlsauth_key, tlsauth_cert, host_filter)
