# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler module functions
"""

import json
from csv import DictWriter, QUOTE_ALL
from datetime import datetime, timedelta
from http import HTTPStatus
from io import StringIO

from flask import current_app, jsonify, render_template
from pytimeparse import parse as timeparse
from sqlalchemy import case, delete, func, or_, not_, select, update
from sqlalchemy.sql.functions import coalesce

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.storage.forms import AnnotateForm, TagMultiidForm
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.utils import filter_query, windowed_query


def get_related_models(model_name, model_id):
    """get related host/service to bind vuln/note"""

    host, service = None, None
    if model_name == 'host':
        host = Host.query.get(model_id)
    elif model_name == 'service':
        service = Service.query.get(model_id)
        host = service.host
    return host, service


def annotate_model(model, model_id):
    """annotate model route"""

    model = model.query.get(model_id)
    form = AnnotateForm(obj=model)

    if form.validate_on_submit():
        form.populate_obj(model)
        db.session.commit()
        return '', HTTPStatus.OK

    return render_template('storage/annotate.html', form=form)


def tag_add(model, tag):
    """add tag to model in sqla trackable way"""

    val = [tag] if isinstance(tag, str) else tag
    model.tags = list(set((model.tags or []) + val))


def tag_remove(model, tag):
    """remove tag from model in sqla trackable way"""

    model.tags = [x for x in (model.tags or []) if x != tag]


def tag_model_multiid(model_class):
    """tag model by id"""

    form = TagMultiidForm()
    if form.validate_on_submit():
        tag = form.tag.data
        for item in model_class.query.filter(model_class.id.in_([tmp.data for tmp in form.ids.entries])).all():
            # full assignment must be used for sqla to realize the change
            if form.action.data == 'set':
                tag_add(item, tag)
            if form.action.data == 'unset':
                tag_remove(item, tag)
        db.session.commit()
        return '', HTTPStatus.OK

    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


def url_for_ref(ref):
    """generate url for ref; reimplemented js function storage pagepart url_for_ref"""

    refgen = {
        'URL': lambda d: d,
        'CVE': lambda d: 'https://cvedetails.com/cve/CVE-' + d,
        'NSS': lambda d: 'https://www.tenable.com/plugins/nessus/' + d,
        'BID': lambda d: 'https://www.securityfocus.com/bid/' + d,
        'CERT': lambda d: 'https://www.kb.cert.org/vuls/id/' + d,
        'EDB': lambda d: 'https://www.exploit-db.com/exploits/' + d.replace('ID-', ''),
        'MSF': lambda d: 'https://www.rapid7.com/db/?q=' + d,
        'MSFT': lambda d: 'https://technet.microsoft.com/en-us/security/bulletin/' + d,
        'MSKB': lambda d: 'https://support.microsoft.com/en-us/help/' + d,
        'SN': lambda d: 'SN-' + d
    }
    try:
        matched = ref.split('-', maxsplit=1)
        return refgen[matched[0]](matched[1])
    except (IndexError, KeyError):
        pass
    return ref


def trim_rdata(rdata):
    """trimdata if requested by app config, spreadsheet processors has issues if cell data is larger than X"""

    content_trimmed = False
    for key, val in rdata.items():
        if current_app.config['SNER_TRIM_REPORT_CELLS'] and val and (len(val) > current_app.config['SNER_TRIM_REPORT_CELLS']):
            rdata[key] = 'TRIMMED'
            content_trimmed = True
    return rdata, content_trimmed


def list_to_lines(data):
    """cast list to lines or empty string"""

    return '\n'.join(data) if data else ''


def vuln_report(qfilter=None, group_by_host=False):  # pylint: disable=too-many-locals
    """generate report from storage data"""

    host_address_format = case([(func.family(Host.address) == 6, func.concat('[', func.host(Host.address), ']'))], else_=func.host(Host.address))
    host_ident = coalesce(Vuln.via_target, Host.hostname, host_address_format)
    endpoint_address = func.concat_ws(':', host_address_format, Service.port)
    endpoint_hostname = func.concat_ws(':', host_ident, Service.port)

    # note1: refs (itself and array) must be unnested in order to be correctly uniq and agg as individual elements by used axis
    # note2: unnesting refs should be implemented as
    # SELECT vuln.name, array_remove(array_agg(urefs.ref), NULL) FROM vuln
    #   LEFT OUTER JOIN LATERAL unnest(vuln.refs) as urefs(ref) ON TRUE
    # GROUP BY vuln.name;`
    # but could not construct appropriate sqla expression `.label('x(y)')` always rendered as string instead of 'table with column'
    unnested_refs = db.session.query(Vuln.id, func.unnest(Vuln.refs).label('ref')).subquery()

    query = db.session \
        .query(
            Vuln.name.label('vulnerability'),
            Vuln.descr.label('description'),
            func.text(Vuln.severity).label('severity'),
            Vuln.tags,
            func.array_agg(func.distinct(host_ident)).label('host_ident'),
            func.array_agg(func.distinct(endpoint_address)).label('endpoint_address'),
            func.array_agg(func.distinct(endpoint_hostname)).label('endpoint_hostname'),
            func.array_remove(func.array_agg(func.distinct(unnested_refs.c.ref)), None).label('references')
        ) \
        .outerjoin(Host, Vuln.host_id == Host.id) \
        .outerjoin(Service, Vuln.service_id == Service.id) \
        .outerjoin(unnested_refs, Vuln.id == unnested_refs.c.id) \
        .group_by(Vuln.name, Vuln.descr, Vuln.severity, Vuln.tags)

    if group_by_host:
        query = query.group_by(host_ident)

    if not (query := filter_query(query, qfilter)):
        raise ValueError('failed to filter query')

    content_trimmed = False
    fieldnames = [
        'id', 'asset', 'vulnerability', 'severity', 'advisory', 'state',
        'endpoint_address', 'description', 'tags', 'endpoint_hostname', 'references'
    ]
    output_buffer = StringIO()
    output = DictWriter(output_buffer, fieldnames, restval='', extrasaction='ignore', quoting=QUOTE_ALL)

    output.writeheader()
    for row in query.all():
        rdata = row._asdict()

        # must count endpoints, multiple addrs can coline in hostnames
        if group_by_host:
            rdata['asset'] = rdata['host_ident'][0]
        else:
            rdata['asset'] = rdata['host_ident'][0] if len(rdata['endpoint_address']) == 1 else 'misc'
        for col in ['endpoint_address', 'endpoint_hostname', 'tags']:
            rdata[col] = list_to_lines(rdata[col])
        rdata['references'] = list_to_lines(map(url_for_ref, rdata['references']))

        rdata, trim_trigger = trim_rdata(rdata)
        content_trimmed |= trim_trigger
        output.writerow(rdata)

    if content_trimmed:
        output.writerow({'asset': 'WARNING: some cells were trimmed'})
    return output_buffer.getvalue()


def vuln_export(qfilter=None):
    """export all vulns in storage without aggregation"""

    host_address_format = case([(func.family(Host.address) == 6, func.concat('[', func.host(Host.address), ']'))], else_=func.host(Host.address))
    host_ident = coalesce(Vuln.via_target, Host.hostname, host_address_format)
    endpoint_address = func.concat_ws(':', host_address_format, Service.port)
    endpoint_hostname = func.concat_ws(':', host_ident, Service.port)

    query = db.session \
        .query(
            host_ident.label('host_ident'),
            Vuln.name.label('vulnerability'),
            Vuln.descr.label('description'),
            Vuln.data,
            func.text(Vuln.severity).label('severity'),
            Vuln.tags,
            endpoint_address.label('endpoint_address'),
            endpoint_hostname.label('endpoint_hostname'),
            Vuln.refs.label('references')
        ) \
        .outerjoin(Host, Vuln.host_id == Host.id) \
        .outerjoin(Service, Vuln.service_id == Service.id)

    if not (query := filter_query(query, qfilter)):
        raise ValueError('failed to filter query')

    content_trimmed = False
    fieldnames = [
        'id', 'host_ident', 'vulnerability', 'severity', 'description', 'data',
        'tags', 'endpoint_address', 'endpoint_hostname', 'references'
    ]
    output_buffer = StringIO()
    output = DictWriter(output_buffer, fieldnames, restval='', quoting=QUOTE_ALL)

    output.writeheader()
    for row in query.all():
        rdata = row._asdict()

        rdata['tags'] = list_to_lines(rdata['tags'])
        rdata['references'] = list_to_lines(map(url_for_ref, rdata['references']))
        rdata, trim_trigger = trim_rdata(rdata)
        content_trimmed |= trim_trigger
        output.writerow(rdata)

    if content_trimmed:
        output.writerow({'host_ident': 'WARNING: some cells were trimmed'})
    return output_buffer.getvalue()


def db_host(address, flag_required=False):
    """query upsert host object"""

    query = Host.query.filter(Host.address == address)
    return query.one() if flag_required else query.one_or_none()


def db_service(host_address, proto, port, flag_required=False):
    """query upsert service object"""

    query = Service.query.outerjoin(Host).filter(Host.address == host_address, Service.proto == proto, Service.port == port)
    return query.one() if flag_required else query.one_or_none()


def db_vuln(host_address, name, xtype, service_proto=None, service_port=None, via_target=None):  # pylint: disable=too-many-arguments
    """query upsert vuln object"""

    query = Vuln.query.outerjoin(Host, Vuln.host_id == Host.id).outerjoin(Service, Vuln.service_id == Service.id).filter(
        Host.address == host_address,
        Vuln.name == name,
        Vuln.xtype == xtype,
        Service.proto == service_proto,
        Service.port == service_port,
        Vuln.via_target == via_target
    )
    return query.one_or_none()


def db_note(host_address, xtype, service_proto=None, service_port=None, via_target=None):
    """query upsert note object"""

    query = Note.query.outerjoin(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id).filter(
        Host.address == host_address,
        Note.xtype == xtype,
        Service.proto == service_proto,
        Service.port == service_port,
        Note.via_target == via_target
    )
    return query.one_or_none()


class StorageManager:
    """storage app logic"""

    @staticmethod
    def import_parsed_dry(pidb):
        """check pidb for new storage items"""

        for ihost in pidb.hosts:
            host = db_host(ihost.address)
            if not host:
                print(f'storage update new host: {ihost}')

        for iservice in pidb.services:
            service = db_service(pidb.hosts.by.iid[iservice.host_iid].address, iservice.proto, iservice.port)
            if not service:
                print(f'storage update new service: {iservice}')

        for ivuln in pidb.vulns:
            service = pidb.services.by.iid[ivuln.service_iid] if (ivuln.service_iid is not None) else None
            vuln = db_vuln(
                pidb.hosts.by.iid[ivuln.host_iid].address,
                ivuln.name,
                ivuln.xtype,
                service.proto if service else None,
                service.port if service else None,
                ivuln.via_target
            )
            if not vuln:
                print(f'storage update new vuln: {ivuln}')

        for inote in pidb.notes:
            service = pidb.services.by.iid[inote.service_iid] if (inote.service_iid is not None) else None
            note = db_note(
                pidb.hosts.by.iid[inote.host_iid].address,
                inote.xtype,
                service.proto if service else None,
                service.port if service else None,
                inote.via_target
            )
            if not note:
                print(f'storage update new note: {inote}')

    @staticmethod
    def import_parsed(pidb, addtags=None):  # pylint: disable=too-many-branches
        """import"""

        # import hosts
        for ihost in pidb.hosts:
            host = db_host(ihost.address)
            if not host:
                host = Host(address=ihost.address)
                db.session.add(host)
                current_app.logger.info(f'storage update new host {host}')
            host.update(ihost)
            if addtags:
                tag_add(host, addtags)

            if ihost.hostnames:
                note = db_note(ihost.address, 'hostnames')
                if not note:
                    note = Note(host=host, xtype='hostnames', data='[]')
                    db.session.add(note)
                note.data = json.dumps(list(set(json.loads(note.data) + ihost.hostnames)))
        db.session.commit()

        # import services
        for iservice in pidb.services:
            host = db_host(pidb.hosts.by.iid[iservice.host_iid].address, flag_required=True)
            service = db_service(host.address, iservice.proto, iservice.port)
            if not service:
                service = Service(host=host, proto=iservice.proto, port=iservice.port)
                db.session.add(service)
                current_app.logger.info(f'storage update new service {service}')
            service.update(iservice)
            if addtags:
                tag_add(service, addtags)
        db.session.commit()

        # import vulns
        for ivuln in pidb.vulns:
            host = db_host(pidb.hosts.by.iid[ivuln.host_iid].address, flag_required=True)
            service = (
                db_service(
                    host.address,
                    pidb.services.by.iid[ivuln.service_iid].proto,
                    pidb.services.by.iid[ivuln.service_iid].port,
                    flag_required=True
                )
                if ivuln.service_iid is not None
                else None
            )
            vuln = db_vuln(
                host.address,
                ivuln.name,
                ivuln.xtype,
                service.proto if service else None,
                service.port if service else None,
                ivuln.via_target
            )
            if not vuln:
                vuln = Vuln(host=host, name=ivuln.name, xtype=ivuln.xtype, service=service, via_target=ivuln.via_target)
                db.session.add(vuln)
                current_app.logger.info(f'storage update new vuln {vuln}')
            vuln.update(ivuln)
            if addtags:
                tag_add(vuln, addtags)
        db.session.commit()

        # import notes
        for inote in pidb.notes:
            host = db_host(pidb.hosts.by.iid[inote.host_iid].address, flag_required=True)
            service = (
                db_service(
                    host.address,
                    pidb.services.by.iid[inote.service_iid].proto,
                    pidb.services.by.iid[inote.service_iid].port,
                    flag_required=True
                )
                if inote.service_iid is not None
                else None
            )
            note = db_note(host.address, inote.xtype, service.proto if service else None, service.port if service else None, inote.via_target)
            if not note:
                note = Note(host=host, xtype=inote.xtype, service=service, via_target=inote.via_target)
                db.session.add(note)
                current_app.logger.info(f'storage update new note {note}')
            note.update(inote)
            if addtags:
                tag_add(note, addtags)
        db.session.commit()

    @staticmethod
    def get_all_six_address():
        """return all host ipv6 addresses"""

        return db.session.connection().execute(select(Host.address).filter(func.family(Host.address) == 6)).scalars().all()

    @staticmethod
    def get_rescan_hosts(interval):
        """rescan hosts from storage; discovers new services on hosts"""

        now = datetime.utcnow()
        rescan_horizont = now - timedelta(seconds=timeparse(interval))
        query = Host.query.filter(or_(Host.rescan_time < rescan_horizont, Host.rescan_time == None))  # noqa: E501, E711  pylint: disable=singleton-comparison

        rescan, ids = [], []
        for host in windowed_query(query, Host.id):
            rescan.append(host.address)
            ids.append(host.id)

        # orm is bypassed for performance reasons in case of large rescans
        db.session.connection().execute(update(Host).where(Host.id.in_(ids)).values(rescan_time=now))
        db.session.commit()
        db.session.expire_all()

        return rescan

    @staticmethod
    def get_rescan_services(interval):
        """rescan services from storage; update known services info"""

        now = datetime.utcnow()
        rescan_horizont = now - timedelta(seconds=timeparse(interval))
        query = Service.query.filter(or_(Service.rescan_time < rescan_horizont, Service.rescan_time == None))  # noqa: E501,E711  pylint: disable=singleton-comparison

        rescan, ids = [], []
        for service in windowed_query(query, Service.id):
            item = f'{service.proto}://{format_host_address(service.host.address)}:{service.port}'
            rescan.append(item)
            ids.append(service.id)

        # orm is bypassed for performance reasons in case of large rescans
        db.session.connection().execute(update(Service).where(Service.id.in_(ids)).values(rescan_time=now))
        db.session.commit()
        db.session.expire_all()

        return rescan

    @staticmethod
    def cleanup_storage():
        """clean up storage from various import artifacts"""
        # bypassing ORM for performance reasons
        conn = db.session.connection()

        # remove any but open:* state services
        services_to_delete = conn.execute(select(
            Service.id,
            Service.proto,
            Service.port,
            Host.address.label('host_address')
        ).join(Host).filter(not_(Service.state.ilike('open:%')))).all()
        for service in services_to_delete:
            current_app.logger.info(
                    'storage update delete service '
                    f'<Service {service.id}: {format_host_address(service.host_address)} {service.proto}.{service.port}>'
            )
        conn.execute(delete(Service).filter(Service.id.in_([x[0] for x in services_to_delete])))

        # remove hosts without any data attribute, service, vuln or note
        hosts_noinfo = conn.execute(
            select(Host.id).filter(or_(Host.os == '', Host.os == None), or_(Host.comment == '', Host.comment == None))  # noqa: E501,E711  pylint: disable=singleton-comparison
        ).scalars().all()
        hosts_noservices = conn.execute(
            select(Host.id).outerjoin(Service).having(func.count(Service.id) == 0).group_by(Host.id)
        ).scalars().all()
        hosts_novulns = conn.execute(select(Host.id).outerjoin(Vuln).having(func.count(Vuln.id) == 0).group_by(Host.id)).scalars().all()
        hosts_nonotes = conn.execute(select(Host.id).outerjoin(Note).having(func.count(Note.id) == 0).group_by(Host.id)).scalars().all()

        hosts_to_delete = list(set(hosts_noinfo) & set(hosts_noservices) & set(hosts_novulns) & set(hosts_nonotes))
        for host in conn.execute(select(Host.id, Host.address, Host.hostname).filter(Host.id.in_(hosts_to_delete))).all():
            current_app.logger.info(f'storage update delete host <Host {host.id}: {host.address} {host.hostname}>')
        conn.execute(delete(Host).filter(Host.id.in_(hosts_to_delete)))

        # also remove all hosts not having any info but one note xtype hostnames
        hosts_only_one_note = conn.execute(select(Host.id).outerjoin(Note).having(func.count(Note.id) == 1).group_by(Host.id)).scalars().all()
        hosts_only_note_hostnames = conn.execute(
            select(Host.id).join(Note).filter(Host.id.in_(hosts_only_one_note), Note.xtype == 'hostnames')
        ).scalars().all()

        hosts_to_delete = list(set(hosts_noinfo) & set(hosts_noservices) & set(hosts_novulns) & set(hosts_only_note_hostnames))
        for host in conn.execute(select(Host.id, Host.address, Host.hostname).filter(Host.id.in_(hosts_to_delete))).all():
            current_app.logger.info(f'storage update delete host <Host {host.id}: {host.address} {host.hostname}>')
        conn.execute(delete(Host).filter(Host.id.in_(hosts_to_delete)))

        db.session.commit()
        db.session.expire_all()
