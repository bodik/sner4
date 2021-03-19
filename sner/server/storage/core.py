# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler module functions
"""

import json
from csv import DictWriter, QUOTE_ALL
from http import HTTPStatus
from io import StringIO

from flask import current_app, jsonify, render_template
from sqlalchemy import case, func

from sner.server.extensions import db
from sner.server.storage.forms import AnnotateForm, TagMultiidForm
from sner.server.storage.models import Host, Note, Service, Vuln


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

    model.tags = list(set((model.tags or []) + [tag]))


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

    return jsonify({'title': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


def import_parsed(parsed_items_db):
    """import parsed objects"""

    import_hosts(parsed_items_db)
    import_services(parsed_items_db)
    import_vulns(parsed_items_db)
    import_notes(parsed_items_db)


def import_hosts(pidb):
    """import hosts from parsed data"""

    for ihost in pidb.hosts.values():
        host = Host.query.filter(Host.address == ihost.address).one_or_none()
        if not host:
            host = Host(address=ihost.address)
            db.session.add(host)

        host.update(ihost)
        if ihost.hostnames:
            note = Note.query.filter(Note.host == host, Note.xtype == 'hostnames').one_or_none()
            if not note:
                note = Note(host=host, xtype='hostnames', data='[]')
                db.session.add(note)
            note.data = json.dumps(list(set(json.loads(note.data) + ihost.hostnames)))

    db.session.commit()


def import_services(pidb):
    """import services from parsed data"""

    for iservice in pidb.services.values():
        host = Host.query.filter(Host.address == pidb.hosts[iservice.host_handle].address).one()

        service = Service.query.filter(Service.host == host, Service.proto == iservice.proto, Service.port == iservice.port).one_or_none()
        if not service:
            service = Service(host=host, proto=iservice.proto, port=iservice.port)
            db.session.add(service)

        service.update(iservice)

    db.session.commit()


def import_vulns(pidb):
    """import vulns from parsed data"""

    for ivuln in pidb.vulns.values():
        host = Host.query.filter(Host.address == pidb.hosts[ivuln.host_handle].address).one()
        service = None
        if ivuln.service_handle:
            service = Service.query.filter(
                Service.host == host,
                Service.proto == pidb.services[ivuln.service_handle].proto,
                Service.port == pidb.services[ivuln.service_handle].port
            ).one()

        vuln = Vuln.query.filter(
            Vuln.host == host,
            Vuln.service == service,
            Vuln.via_target == ivuln.via_target,
            Vuln.xtype == ivuln.xtype
        ).one_or_none()
        if not vuln:
            vuln = Vuln(host=host, service=service, via_target=ivuln.via_target, xtype=ivuln.xtype)
            db.session.add(vuln)

        vuln.update(ivuln)

    db.session.commit()


def import_notes(pidb):
    """import vulns from parsed data"""

    for inote in pidb.notes.values():
        host = Host.query.filter(Host.address == pidb.hosts[inote.host_handle].address).one()
        service = None
        if inote.service_handle:
            service = Service.query.filter(
                Service.host == host,
                Service.proto == pidb.services[inote.service_handle].proto,
                Service.port == pidb.services[inote.service_handle].port
            ).one()

        note = Note.query.filter(
            Note.host == host,
            Note.service == service,
            Note.via_target == inote.via_target,
            Note.xtype == inote.xtype
        ).one_or_none()
        if not note:
            note = Note(host=host, service=service, via_target=inote.via_target, xtype=inote.xtype)
            db.session.add(note)

        note.update(inote)

    db.session.commit()


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


def vuln_report():
    """generate report from storage data"""

    host_ident = case([(func.char_length(Host.hostname) > 0, Host.hostname)], else_=func.host(Host.address))
    endpoint_address = func.concat_ws(':', Host.address, Service.port)
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


def vuln_export():
    """export all vulns in storage without aggregation"""

    host_ident = case([(func.char_length(Host.hostname) > 0, Host.hostname)], else_=func.host(Host.address))
    endpoint_address = func.concat_ws(':', Host.address, Service.port)
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
