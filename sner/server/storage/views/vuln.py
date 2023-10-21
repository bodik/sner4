# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vuln views
"""

import json
from datetime import datetime
from http import HTTPStatus

from datatables import ColumnDT, DataTables
from flask import current_app, jsonify, redirect, render_template, request, Response, url_for
from sqlalchemy import cast, func, literal_column, or_, select, union

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.storage.core import (
    model_annotate,
    filtered_vuln_tags_query,
    get_related_models,
    model_delete_multiid,
    model_tag_multiid,
    vuln_export,
    vuln_report
)
from sner.server.storage.forms import MultiidForm, TagMultiidForm, VulnMulticopyForm, VulnForm
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.storage.views import blueprint
from sner.server.utils import filter_query, relative_referrer, SnerJSONEncoder, valid_next_url


@blueprint.route('/vuln/list')
@session_required('operator')
def vuln_list_route():
    """list vulns"""

    return render_template('storage/vuln/list.html')


@blueprint.route('/vuln/list.json', methods=['GET', 'POST'])
@session_required('operator')
def vuln_list_json_route():
    """list vulns, data endpoint"""

    columns = [
        ColumnDT(literal_column('1'), mData='_select', search_method='none', global_search=False),
        ColumnDT(Vuln.id, mData='id'),
        ColumnDT(Host.id, mData='host_id'),
        ColumnDT(Host.address, mData='host_address'),
        ColumnDT(Host.hostname, mData='host_hostname'),
        ColumnDT(Service.proto, mData='service_proto'),
        ColumnDT(Service.port, mData='service_port'),
        ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
        ColumnDT(Vuln.via_target, mData='via_target'),
        ColumnDT(Vuln.name, mData='name'),
        ColumnDT(Vuln.xtype, mData='xtype'),
        ColumnDT(Vuln.severity, mData='severity'),
        ColumnDT(Vuln.refs, mData='refs'),
        ColumnDT(Vuln.tags, mData='tags'),
        ColumnDT(Vuln.comment, mData='comment'),
        ColumnDT(Vuln.created, mData='created'),
        ColumnDT(Vuln.modified, mData='modified'),
        ColumnDT(Vuln.rescan_time, mData='rescan_time'),
        ColumnDT(Vuln.import_time, mData='import_time'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Vuln).outerjoin(Host, Vuln.host_id == Host.id).outerjoin(Service, Vuln.service_id == Service.id)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    vulns = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulns, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vuln/add/<model_name>/<model_id>', methods=['GET', 'POST'])
@session_required('operator')
def vuln_add_route(model_name, model_id):
    """add vuln to host or service"""

    host, service = get_related_models(model_name, model_id)
    form = VulnForm(host_id=host.id, service_id=(service.id if service else None))

    if form.validate_on_submit():
        vuln = Vuln()
        form.populate_obj(vuln)
        db.session.add(vuln)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

    return render_template('storage/vuln/addedit.html', form=form, host=host, service=service)


@blueprint.route('/vuln/edit/<vuln_id>', methods=['GET', 'POST'])
@session_required('operator')
def vuln_edit_route(vuln_id):
    """edit vuln"""

    vuln = Vuln.query.get(vuln_id)
    form = VulnForm(obj=vuln, return_url=relative_referrer())

    if form.validate_on_submit():
        form.populate_obj(vuln)
        db.session.commit()
        if valid_next_url(form.return_url.data):
            return redirect(form.return_url.data)

    return render_template('storage/vuln/addedit.html', form=form, host=vuln.host, service=vuln.service)


@blueprint.route('/vuln/delete/<vuln_id>', methods=['GET', 'POST'])
def vuln_delete_route(vuln_id):
    """delete vuln"""

    form = ButtonForm()
    if form.validate_on_submit():
        vuln = Vuln.query.get(vuln_id)
        db.session.delete(vuln)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

    return render_template('button-delete.html', form=form)


@blueprint.route('/vuln/annotate/<model_id>', methods=['GET', 'POST'])
@session_required('operator')
def vuln_annotate_route(model_id):
    """annotate vuln"""
    return model_annotate(Vuln, model_id)


@blueprint.route('/vuln/view/<vuln_id>')
@session_required('operator')
def vuln_view_route(vuln_id):
    """view vuln"""

    vuln = Vuln.query.get(vuln_id)
    return render_template('storage/vuln/view.html', vuln=vuln, button_form=ButtonForm())


@blueprint.route('/vuln/delete_multiid', methods=['POST'])
@session_required('operator')
def vuln_delete_multiid_route():
    """delete multiple vulns route"""

    form = MultiidForm()
    if form.validate_on_submit():
        model_delete_multiid(Vuln, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/vuln/tag_multiid', methods=['POST'])
@session_required('operator')
def vuln_tag_multiid_route():
    """tag multiple route"""

    form = TagMultiidForm()
    if form.validate_on_submit():
        model_tag_multiid(Vuln, form.action.data, form.tag.data, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/vuln/grouped')
@session_required('operator')
def vuln_grouped_route():
    """view grouped vulns"""

    return render_template('storage/vuln/grouped.html')


@blueprint.route('/vuln/grouped.json', methods=['GET', 'POST'])
@session_required('operator')
def vuln_grouped_json_route():
    """view grouped vulns, data endpoint"""

    vuln_tags_query, vuln_tags_column = filtered_vuln_tags_query(current_app.config["SNER_VULN_GROUP_IGNORE_TAG_PREFIX"])

    columns = [
        ColumnDT(Vuln.name, mData='name'),
        ColumnDT(Vuln.severity, mData='severity'),
        ColumnDT(vuln_tags_column, mData='tags'),
        ColumnDT(func.count(Vuln.id), mData='cnt_vulns', global_search=False),
    ]
    query = (
        db.session.query()
        .select_from(Vuln)
        .outerjoin(vuln_tags_query, Vuln.id == vuln_tags_query.c.id)
        .outerjoin(Host, Vuln.host_id == Host.id)  # allows filter over host attrs
        .group_by(Vuln.name, Vuln.severity, vuln_tags_query.c.utags)
    )
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    vulns = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulns, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vuln/report')
@session_required('operator')
def vuln_report_route():
    """generate vulns report"""

    return Response(
        vuln_report(request.values.get('filter'), request.values.get('group_by_host')),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=report-{datetime.now().isoformat()}.csv'}
    )


@blueprint.route('/vuln/export')
@session_required('operator')
def vuln_export_route():
    """vulns export"""

    return Response(
        vuln_export(request.values.get('filter')),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=export-{datetime.now().isoformat()}.csv'}
    )


@blueprint.route('/vuln/multicopy/<int:vuln_id>', methods=['GET', 'POST'])
@session_required('operator')
def vuln_multicopy_route(vuln_id):
    """copu vuln"""

    vuln = Vuln.query.get(vuln_id)
    form = VulnMulticopyForm(obj=vuln)

    if form.validate_on_submit():
        new_vulns = []
        for endpoint in form.endpoints.data:
            vuln = Vuln()
            form.populate_obj(vuln)
            vuln.update(endpoint)
            db.session.add(vuln)
            new_vulns.append(vuln)
        db.session.commit()

        filter_string = 'Vuln.id in ' + json.dumps([vuln_id] + [x.id for x in new_vulns])
        return redirect(url_for('storage.vuln_list_route', filter=filter_string))

    return render_template('storage/vuln/multicopy.html', form=form)


@blueprint.route('/vuln/multicopy_endpoints.json', methods=['GET', 'POST'])
@session_required('operator')
def vuln_multicopy_endpoints_json_route():
    """multicopy endpoints endpoint"""

    # returned data does not require dummy _select column because DT instance
    # does not use serverSide processing/sorting (unlinke other DT instances
    # host/list, service/list, ...)

    query = select(
        func.jsonb_build_object('host_id', Host.id).label("endpoint_id"),
        Host.address.label("host_address"),
        Host.hostname.label("host_hostname"),
    ).select_from(Host)
    hosts = [
        {**x._asdict(), "service_proto": None, "service_port": None, "service_info": None}
        for x in db.session.execute(query).all()
    ]

    query = select(
        func.jsonb_build_object('host_id', Host.id, 'service_id', Service.id).label("endpoint_id"),
        Host.address.label("host_address"),
        Host.hostname.label("host_hostname"),
        Service.proto.label("service_proto"),
        Service.port.label("service_port"),
        Service.info.label("service_info")
    ).select_from(Service).outerjoin(Host, Service.host_id == Host.id)
    services = [x._asdict() for x in db.session.execute(query).all()]

    data = {"data": sorted(hosts + services, key=lambda item: (item['host_address'], item['service_port'] or 0))}
    return Response(json.dumps(data, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vuln_addedit_host_autocomplete')
@session_required('operator')
def vuln_addedit_host_autocomplete_route():
    """autocomplete suggestions for host"""

    term = request.args.get('term', '')
    if not term:
        return jsonify([])

    hosts = Host.query.filter(
        or_(cast(Host.address, db.String).ilike(f"%{term}%"), Host.hostname.ilike(f"%{term}%"))
    ).limit(current_app.config['SNER_AUTOCOMPLETE_LIMIT']).all()
    data = [
        {'value': host.id, 'label': f'{host.address} (hostname: {host.hostname} id:{host.id})'}
        for host in hosts
    ]

    return jsonify(data)


@blueprint.route('/vuln_addedit_service_autocomplete')
@session_required('operator')
def vuln_addedit_service_autocomplete_route():
    """autocomplete suggestions for service"""

    host_id = request.args.get('host_id', '', str)
    service_term = request.args.get('service_term', '')
    if not host_id.isnumeric():
        return jsonify([])

    data = []
    services = Service.query.filter(
        Service.host_id == host_id,
        or_(
            Service.proto.ilike(f'%{service_term}%'),
            cast(Service.port, db.String).ilike(f"%{service_term}%")
        )
    ).all()
    for service in services:
        data.append({
            'value': service.id,
            'label': f'{service.proto}/{service.port} {service.host.address} (hostname: {service.host.hostname} id:{service.host.id})'
        })

    return jsonify(data)


@blueprint.route('/vuln_addedit_viatarget_autocomplete')
@session_required('operator')
def vuln_addedit_viatarget_autocomplete_route():
    """autocomplete suggestions for via_target"""

    host_id = request.args.get('host_id', '', str)
    target_term = request.args.get('target_term', '')
    if not host_id.isnumeric():
        return jsonify([])

    data = []
    query = union(
        select(Vuln.via_target).filter(Vuln.host_id == host_id, Vuln.via_target.ilike(f"%{target_term}%")),
        select(Note.via_target).filter(Note.host_id == host_id, Note.via_target.ilike(f"%{target_term}%"))
    )
    items = db.session.execute(query).scalars().all()
    data = items

    return jsonify(data)
