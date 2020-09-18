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
            'MSF': lambda d: 'https://www.rapid7.com/db/?q=' + d,
            'SN': lambda d: 'SN-' + d
        }
        try:
            matched = ref.split('-', maxsplit=1)
            return refgen[matched[0]](matched[1])
        except (IndexError, KeyError):
            pass
        return ref

    endpoint_address = func.concat_ws(':', Host.address, Service.port)
    endpoint_hostname = func.concat_ws(
        ':', case([(func.char_length(Host.hostname) > 0, Host.hostname)], else_=func.host(Host.address)), Service.port)
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

    content_trimmed = False
    fieldnames = [
        'id', 'asset', 'vulnerability', 'severity', 'advisory', 'state',
        'endpoint_address', 'description', 'tags', 'endpoint_hostname', 'references']
    output_buffer = StringIO()
    output = DictWriter(output_buffer, fieldnames, restval='', quoting=QUOTE_ALL)

    output.writeheader()
    for row in query.all():
        rdata = row._asdict()

        if (len(rdata['endpoint_address']) == 1) and (len(rdata['endpoint_hostname']) == 1):
            rdata['asset'] = rdata['endpoint_hostname'][0]
        else:
            rdata['asset'] = 'misc'

        for col in ['endpoint_address', 'endpoint_hostname', 'tags']:
            rdata[col] = '\n'.join(rdata[col]) if rdata[col] else ''
        rdata['references'] = '\n'.join([url_for_ref(ref) for ref in rdata['references']]) if rdata['references'] else ''

        # do cell trimming, spreadsheet processors has issues if cell data is larger than X
        for key, val in rdata.items():
            if current_app.config['SNER_TRIM_REPORT_CELLS'] and val and (len(val) > current_app.config['SNER_TRIM_REPORT_CELLS']):
                rdata[key] = 'TRIMMED'
                content_trimmed = True

        output.writerow(rdata)

    if content_trimmed:
        output.writerow({'asset': 'WARNING: some cells were trimmed'})
    return output_buffer.getvalue()


def import_parsed(hosts, services, vulns, notes):
    """import parsed objects"""

    import_hosts(hosts)
    import_services(services)
    import_vulns(vulns)
    import_notes(notes)


def import_hosts(parsed_hosts):
    """import hosts from parsed data"""

    for ihost in parsed_hosts:
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


def import_services(parsed_services):
    """import services from parsed data"""

    for iservice in parsed_services:
        host = Host.query.filter(Host.address == iservice.handle['host']).one()

        service = Service.query.filter(Service.host == host, Service.proto == iservice.proto, Service.port == iservice.port).one_or_none()
        if not service:
            service = Service(host=host, proto=iservice.proto, port=iservice.port)
            db.session.add(service)

        service.update(iservice)

    db.session.commit()


def import_vulns(parsed_vulns):
    """import vulns from parsed data"""

    for ivuln in parsed_vulns:
        host = Host.query.filter(Host.address == ivuln.handle['host']).one()
        service_id = func.concat(Service.proto, '/', Service.port)
        service = Service.query.filter(Service.host == host, service_id == ivuln.handle.get('service')).one_or_none()

        vuln = Vuln.query.filter(Vuln.host == host, Vuln.service == service, Vuln.xtype == ivuln.handle['vuln']).one_or_none()
        if not vuln:
            vuln = Vuln(host=host, service=service, xtype=ivuln.xtype)
            db.session.add(vuln)

        vuln.update(ivuln)

    db.session.commit()


def import_notes(parsed_notes):
    """import vulns from parsed data"""

    for inote in parsed_notes:
        host = Host.query.filter(Host.address == inote.handle['host']).one()
        service_id = func.concat(Service.proto, '/', Service.port)
        service = Service.query.filter(Service.host == host, service_id == inote.handle.get('service')).one_or_none()

        note = Note.query.filter(Note.host == host, Note.service == service, Note.xtype == inote.handle['note']).one_or_none()
        if not note:
            note = Note(host=host, service=service, xtype=inote.xtype)
            db.session.add(note)

        note.update(inote)
        if 'vuln' in inote.handle:
            vuln = Vuln.query.filter(Vuln.host == host, Vuln.service == service, Vuln.xtype == inote.handle['vuln']).one()
            vuln.refs = [f'SN-{note.id}'] + vuln.refs

    db.session.commit()
