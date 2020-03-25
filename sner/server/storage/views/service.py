# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage service views
"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, literal_column
from sqlalchemy.dialects import postgresql
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.sqlafilter import filter_parser
from sner.server.storage.core import annotate_model
from sner.server.storage.forms import ServiceForm
from sner.server.storage.models import Host, Service
from sner.server.storage.views import blueprint
from sner.server.utils import relative_referrer, valid_next_url


def service_info_column(crop):
    """return optionally cropped service.info column"""

    if crop:
        return func.array_to_string(func.string_to_array(Service.info, ' ', type_=postgresql.ARRAY(db.String))[1:int(crop)], ' ')
    return Service.info


@blueprint.route('/service/list')
@role_required('operator')
def service_list_route():
    """list services"""

    return render_template('storage/service/list.html')


@blueprint.route('/service/list.json', methods=['GET', 'POST'])
@role_required('operator')
def service_list_json_route():
    """list services, data endpoint"""

    columns = [
        ColumnDT(Service.id, mData='id'),
        ColumnDT(Host.id, mData='host_id'),
        ColumnDT(Host.address, mData='host_address'),
        ColumnDT(Host.hostname, mData='host_hostname'),
        ColumnDT(Service.proto, mData='proto'),
        ColumnDT(Service.port, mData='port'),
        ColumnDT(Service.name, mData='name'),
        ColumnDT(Service.state, mData='state'),
        ColumnDT(Service.info, mData='info'),
        ColumnDT(Service.tags, mData='tags'),
        ColumnDT(Service.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Service).outerjoin(Host)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    services = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(services)


@blueprint.route('/service/add/<host_id>', methods=['GET', 'POST'])
@role_required('operator')
def service_add_route(host_id):
    """add service to host"""

    host = Host.query.get(host_id)
    form = ServiceForm(host_id=host_id)

    if form.validate_on_submit():
        service = Service()
        form.populate_obj(service)
        db.session.add(service)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=service.host_id))

    return render_template('storage/service/addedit.html', form=form, host=host)


@blueprint.route('/service/edit/<service_id>', methods=['GET', 'POST'])
@role_required('operator')
def service_edit_route(service_id):
    """edit service"""

    service = Service.query.get(service_id)
    form = ServiceForm(obj=service, return_url=relative_referrer())

    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        if valid_next_url(form.return_url.data):
            return redirect(form.return_url.data)

    return render_template('storage/service/addedit.html', form=form, host=service.host)


@blueprint.route('/service/delete/<service_id>', methods=['GET', 'POST'])
@role_required('operator')
def service_delete_route(service_id):
    """delete service"""

    form = ButtonForm()

    if form.validate_on_submit():
        service = Service.query.get(service_id)
        db.session.delete(service)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=service.host_id))

    return render_template('button-delete.html', form=form)


@blueprint.route('/service/annotate/<model_id>', methods=['GET', 'POST'])
@role_required('operator')
def service_annotate_route(model_id):
    """annotate service"""
    return annotate_model(Service, model_id)


@blueprint.route('/service/grouped')
@role_required('operator')
def service_grouped_route():
    """view grouped services"""

    return render_template('storage/service/grouped.html')


@blueprint.route('/service/grouped.json', methods=['GET', 'POST'])
@role_required('operator')
def service_grouped_json_route():
    """view grouped services, data endpoint"""

    info_column = service_info_column(request.args.get('crop'))
    columns = [
        ColumnDT(info_column, mData='info'),
        ColumnDT(func.count(Service.id), mData='cnt_services', global_search=False),
    ]
    query = db.session.query().select_from(Service).group_by(info_column)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    services = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(services)
