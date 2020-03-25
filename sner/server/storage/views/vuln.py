# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vuln views
"""

import json
from datetime import datetime
from http import HTTPStatus

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, Response, url_for
from sqlalchemy import func, literal_column
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.sqlafilter import filter_parser
from sner.server.storage.core import annotate_model, get_related_models, tag_model_multiid
from sner.server.storage.commands import vuln_report
from sner.server.storage.forms import MultiidForm, VulnForm
from sner.server.storage.models import Host, Service, Vuln
from sner.server.storage.views import blueprint
from sner.server.utils import relative_referrer, SnerJSONEncoder, valid_next_url


@blueprint.route('/vuln/list')
@role_required('operator')
def vuln_list_route():
    """list vulns"""

    return render_template('storage/vuln/list.html')


@blueprint.route('/vuln/list.json', methods=['GET', 'POST'])
@role_required('operator')
def vuln_list_json_route():
    """list vulns, data endpoint"""

    columns = [
        ColumnDT(literal_column('1'), mData='_select', search_method='none', global_search=False),
        ColumnDT(Vuln.id, mData='id'),
        ColumnDT(Host.id, mData='host_id'),
        ColumnDT(Host.address, mData='host_address'),
        ColumnDT(Host.hostname, mData='host_hostname'),
        ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
        ColumnDT(Vuln.name, mData='name'),
        ColumnDT(Vuln.xtype, mData='xtype'),
        ColumnDT(Vuln.severity, mData='severity'),
        ColumnDT(Vuln.refs, mData='refs'),
        ColumnDT(Vuln.tags, mData='tags'),
        ColumnDT(Vuln.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Vuln).outerjoin(Host, Vuln.host_id == Host.id).outerjoin(Service, Vuln.service_id == Service.id)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    vulns = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulns, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vuln/add/<model_name>/<model_id>', methods=['GET', 'POST'])
@role_required('operator')
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
@role_required('operator')
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
@role_required('operator')
def vuln_annotate_route(model_id):
    """annotate vuln"""
    return annotate_model(Vuln, model_id)


@blueprint.route('/vuln/view/<vuln_id>')
@role_required('operator')
def vuln_view_route(vuln_id):
    """view vuln"""

    vuln = Vuln.query.get(vuln_id)
    return render_template('storage/vuln/view.html', vuln=vuln, button_form=ButtonForm())


@blueprint.route('/vuln/delete_multiid', methods=['POST'])
@role_required('operator')
def vuln_delete_multiid_route():
    """delete multiple vulns route"""

    form = MultiidForm()
    if form.validate_on_submit():
        Vuln.query.filter(Vuln.id.in_([tmp.data for tmp in form.ids.entries])).delete(synchronize_session=False)
        db.session.commit()
        return '', HTTPStatus.OK

    return jsonify({'title': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/vuln/tag_multiid', methods=['POST'])
@role_required('operator')
def vuln_tag_multiid_route():
    """tag multiple route"""
    return tag_model_multiid(Vuln)


@blueprint.route('/vuln/grouped')
@role_required('operator')
def vuln_grouped_route():
    """view grouped vulns"""

    return render_template('storage/vuln/grouped.html')


@blueprint.route('/vuln/grouped.json', methods=['GET', 'POST'])
@role_required('operator')
def vuln_grouped_json_route():
    """view grouped vulns, data endpoint"""

    columns = [
        ColumnDT(Vuln.name, mData='name'),
        ColumnDT(Vuln.severity, mData='severity'),
        ColumnDT(Vuln.tags, mData='tags'),
        ColumnDT(func.count(Vuln.id), mData='cnt_vulns', global_search=False),
    ]
    query = db.session.query().select_from(Vuln).group_by(Vuln.name, Vuln.severity, Vuln.tags)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    vulns = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulns, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vuln/report')
@role_required('operator')
def vuln_report_route():
    """generate vulns report"""

    return Response(
        vuln_report(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=report-%s.csv' % datetime.now().isoformat()})
