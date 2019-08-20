# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage commands
"""

import json
import os
import re
import sys
from csv import DictWriter, QUOTE_ALL
from io import StringIO

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func, or_
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.model.storage import Host, Note, Service, Vuln
from sner.server.parser import registered_parsers
from sner.server.sqlafilter import filter_parser


def vuln_report():
    """generate report from storage data"""

    def url_for_ref(ref):
        """generate url for ref; reimplemented js function storage pagepart url_for_ref"""

        refgen = {
            'URL': lambda d: d,
            'CVE': lambda d: 'https://cvedetails.com/cve/CVE-' + d,
            'NSS': lambda d: 'https://www.tenable.com/plugins/nessus/' + d,
            'BID': lambda d: 'http://www.securityfocus.com/bid/' + d,
            'CERT': lambda d: 'https://www.kb.cert.org/vuls/id/' + d,
            'EDB': lambda d: 'https://www.exploit-db.com/exploits/' + d.replace('ID-', ''),
            'SN': lambda d: 'SN-' + d
        }
        try:
            matched = re.match(r'(.*?)\-(.*)', ref)
            return refgen[matched.group(1)](matched.group(2))
        except (AttributeError, KeyError):
            pass
        return ref

    endpoint_address = func.concat_ws(':', Host.address, Service.port)
    endpoint_hostname = func.concat_ws(':', Host.hostname, Service.port)
    # unnesting refs should be implemented as
    # SELECT vuln.name, array_remove(array_agg(urefs.ref), NULL) FROM vuln
    #   LEFT OUTER JOIN LATERAL unnest(vuln.refs) as urefs(ref) ON TRUE
    # GROUP BY vuln.name;`
    # but could not construct appropriate sqla expression `.label('x(y)')` always rendered as string instead of 'table with column'
    unnested_refs = db.session.query(Vuln.id, func.unnest(Vuln.refs).label('ref')).subquery()
    query = db.session \
        .query(
            Vuln.name.label('vulnerability'),
            Vuln.descr.label('description'),
            Vuln.tags,
            func.array_agg(func.distinct(endpoint_address)).label('endpoint_address'),
            func.array_agg(func.distinct(endpoint_hostname)).label('endpoint_hostname'),
            func.array_remove(func.array_agg(func.distinct(unnested_refs.c.ref)), None).label('references')
        ) \
        .outerjoin(Host, Vuln.host_id == Host.id) \
        .outerjoin(Service, Vuln.service_id == Service.id) \
        .outerjoin(unnested_refs, Vuln.id == unnested_refs.c.id) \
        .group_by(Vuln.name, Vuln.descr, Vuln.tags)

    output_buffer = StringIO()
    fieldnames = [
        'id', 'asset', 'vulnerability', 'severity', 'advisory', 'state',
        'endpoint_address', 'description', 'tags', 'endpoint_hostname', 'references']
    output = DictWriter(output_buffer, fieldnames, restval='', quoting=QUOTE_ALL)

    output.writeheader()
    for row in query.all():
        rdata = row._asdict()

        # set asset name. 'misc' if many, otherwise existing from hostname or address
        if (len(rdata['endpoint_hostname'] or []) > 1) or (len(rdata['endpoint_address'] or []) > 1):
            rdata['asset'] = 'misc'
        else:
            tmp = (rdata['endpoint_hostname'] or []) + (rdata['endpoint_address'] or [])
            if tmp:
                rdata['asset'] = tmp[0]

        # cast array cols to lines
        for col in ['endpoint_address', 'endpoint_hostname', 'tags']:
            rdata[col] = '\n'.join(rdata[col] or [])

        rdata['references'] = '\n'.join([url_for_ref(ref) for ref in rdata['references'] or []])

        output.writerow(rdata)

    return output_buffer.getvalue()


@click.group(name='storage', help='sner.server storage management')
def storage_command():
    """storage commands click group/container"""


@storage_command.command(name='import', help='import data from files')
@with_appcontext
@click.argument('parser')
@click.argument('path', nargs=-1)
def storage_import(path, parser):
    """import data"""

    if parser not in registered_parsers:
        current_app.logger.error('no such parser')
        sys.exit(1)

    parser_impl = registered_parsers[parser]
    for item in path:
        if os.path.isfile(item):
            parser_impl.import_file(item)
    sys.exit(0)


@storage_command.command(name='flush', help='flush all objects from storage')
@with_appcontext
def storage_flush():
    """flush all objects from storage"""

    db.session.query(Host).delete()
    db.session.commit()


@storage_command.command(name='report', help='generate vuln report')
@with_appcontext
def storage_report():
    """generate vuln report"""
    print(vuln_report())


@storage_command.command(name='host-cleanup', help='cleanup hosts; remove hosts not associated with any data (eg. just addresses)')
@with_appcontext
@click.option('--dry', is_flag=True, help='do not actually remove')
def storage_host_cleanup(**kwargs):
    """
    clean up storage, will remove all hosts:
        * without any data attribute set
        * having no service, vuln or note
    """

    services_count = func.count(Service.id)
    vulns_count = func.count(Vuln.id)
    notes_count = func.count(Note.id)
    query_hosts = Host.query \
        .outerjoin(Service, Host.id == Service.host_id).outerjoin(Vuln, Host.id == Vuln.host_id).outerjoin(Note, Host.id == Note.host_id) \
        .filter(
            or_(Host.os == '', Host.os == None),  # noqa: E711  pylint: disable=singleton-comparison
            or_(Host.comment == '', Host.comment == None)  # noqa: E711  pylint: disable=singleton-comparison
        ) \
        .having(services_count == 0).having(vulns_count == 0).having(notes_count == 0).group_by(Host.id)

    if kwargs['dry']:
        for host in query_hosts.all():
            print(host)

        # do not commit, it's dry test
        db.session.rollback()
    else:
        for host in query_hosts.all():
            db.session.delete(host)
        db.session.commit()


@storage_command.command(name='service-list', help='service (filtered) listing')
@with_appcontext
@click.option('--filter', help='filter query')
@click.option('--iponly', is_flag=True, help='show only service.host.address')
@click.option('--long', is_flag=True, help='show service extended info')
def storage_service_list(**kwargs):
    """service listing; used to feed manymap queues from storage data"""

    def fmt_addr(val):
        """format ?ipv6 address"""
        return val if ':' not in val else '[%s]' % val

    def data_default(svc):
        """return tuple for default output"""
        return (svc.proto, fmt_addr(svc.host.address), svc.port)

    def data_long(svc):
        """return tuple for long output"""
        return (svc.proto, fmt_addr(svc.host.address), svc.port, svc.name, svc.state, json.dumps(svc.info))

    def data_iponly(svc):
        """return host.address for ip only output"""
        return svc.host.address

    if kwargs['long'] and kwargs['iponly']:
        current_app.logger.error('--iponly and --long are mutualy exclusive options')
        sys.exit(1)

    query = Service.query
    if kwargs['filter']:
        query = apply_filters(query, filter_parser.parse(kwargs['filter']), do_auto_join=False)

    fmt, fndata = '%s://%s:%d', data_default
    if kwargs['iponly']:
        fmt, fndata = '%s', data_iponly
    elif kwargs['long']:
        fmt, fndata = '%s://%s:%d %s %s %s', data_long
    for tmp in query.all():
        print(fmt % fndata(tmp))


@storage_command.command(name='service-cleanup', help='cleanup services; remove all in "filtered" state')
@with_appcontext
@click.option('--dry', is_flag=True, help='do not actually remove')
def storage_service_cleanup(**kwargs):
    """clean up storage, will remove all services in any of 'filtered' state"""

    query_services = Service.query.filter(Service.state.ilike('filtered%'))
    if kwargs['dry']:
        for service in query_services.all():
            print(service)

        # do not commit, it's dry test
        db.session.rollback()
    else:
        for service in query_services.all():
            db.session.delete(service)
        db.session.commit()
