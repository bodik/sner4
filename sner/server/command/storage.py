"""storage commands"""

import os
import re
import sys
from csv import DictWriter, QUOTE_ALL
from io import StringIO
from zipfile import ZipFile

import click
import magic
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func

from sner.server import db
from sner.server.model.storage import Host, Service, Vuln
from sner.server.parser import registered_parsers


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

    def data_from_file(filename, job_output_datafile):
        with open(filename, 'rb') as ifile:
            mime_type = magic.detect_from_fobj(ifile).mime_type
            if mime_type == 'application/zip':
                with ZipFile(ifile, 'r') as ftmp:
                    data = ftmp.read(job_output_datafile)
            else:
                data = ifile.read()
        return data.decode('utf-8')

    if parser not in registered_parsers:
        current_app.logger.error('no such parser')
        sys.exit(1)

    parser_impl = registered_parsers[parser]
    for item in path:
        if os.path.isfile(item):
            parser_impl.data_to_storage(data_from_file(item, parser_impl.JOB_OUTPUT_DATAFILE))
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
