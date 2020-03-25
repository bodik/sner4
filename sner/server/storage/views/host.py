# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage hosts views
"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, literal_column
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.sqlafilter import filter_parser
from sner.server.storage.core import annotate_model, tag_model_multiid
from sner.server.storage.forms import HostForm
from sner.server.storage.models import Host, Note, Service, Vuln
from sner.server.storage.views import blueprint
from sner.server.utils import relative_referrer, valid_next_url


@blueprint.route('/host/list')
@role_required('operator')
def host_list_route():
    """list hosts"""

    return render_template('storage/host/list.html')


@blueprint.route('/host/list.json', methods=['GET', 'POST'])
@role_required('operator')
def host_list_json_route():
    """list hosts, data endpoint"""

    query_cnt_services = db.session.query(Service.host_id, func.count(Service.id).label('cnt')).group_by(Service.host_id).subquery()
    query_cnt_vulns = db.session.query(Vuln.host_id, func.count(Vuln.id).label('cnt')).group_by(Vuln.host_id).subquery()
    query_cnt_notes = db.session.query(Note.host_id, func.count(Note.id).label('cnt')).group_by(Note.host_id).subquery()
    columns = [
        ColumnDT(Host.id, mData='id'),
        ColumnDT(Host.address, mData='address'),
        ColumnDT(Host.hostname, mData='hostname'),
        ColumnDT(Host.os, mData='os'),
        ColumnDT(func.coalesce(query_cnt_services.c.cnt, 0), mData='cnt_s', global_search=False),
        ColumnDT(func.coalesce(query_cnt_vulns.c.cnt, 0), mData='cnt_v', global_search=False),
        ColumnDT(func.coalesce(query_cnt_notes.c.cnt, 0), mData='cnt_n', global_search=False),
        ColumnDT(Host.tags, mData='tags'),
        ColumnDT(Host.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Host) \
        .outerjoin(query_cnt_services, Host.id == query_cnt_services.c.host_id) \
        .outerjoin(query_cnt_vulns, Host.id == query_cnt_vulns.c.host_id) \
        .outerjoin(query_cnt_notes, Host.id == query_cnt_notes.c.host_id)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    hosts = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(hosts)


@blueprint.route('/host/add', methods=['GET', 'POST'])
@role_required('operator')
def host_add_route():
    """add host"""

    form = HostForm()

    if form.validate_on_submit():
        host = Host()
        form.populate_obj(host)
        db.session.add(host)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=host.id))

    return render_template('storage/host/addedit.html', form=form)


@blueprint.route('/host/edit/<host_id>', methods=['GET', 'POST'])
@role_required('operator')
def host_edit_route(host_id):
    """edit host"""

    host = Host.query.get(host_id)
    form = HostForm(obj=host, return_url=relative_referrer())

    if form.validate_on_submit():
        form.populate_obj(host)
        db.session.commit()
        if valid_next_url(form.return_url.data):
            return redirect(form.return_url.data)

    return render_template('storage/host/addedit.html', form=form)


@blueprint.route('/host/delete/<host_id>', methods=['GET', 'POST'])
@role_required('operator')
def host_delete_route(host_id):
    """delete host"""

    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(Host.query.get(host_id))
        db.session.commit()
        return redirect(url_for('storage.host_list_route'))

    return render_template('button-delete.html', form=form)


@blueprint.route('/host/annotate/<model_id>', methods=['GET', 'POST'])
@role_required('operator')
def host_annotate_route(model_id):
    """annotate vuln"""
    return annotate_model(Host, model_id)


@blueprint.route('/host/view/<host_id>')
@role_required('operator')
def host_view_route(host_id):
    """view host"""

    host = Host.query.get(host_id)
    return render_template('storage/host/view.html', host=host, button_form=ButtonForm())


@blueprint.route('/host/tag_multiid', methods=['POST'])
@role_required('operator')
def host_tag_multiid_route():
    """tag multiple route"""
    return tag_model_multiid(Host)
