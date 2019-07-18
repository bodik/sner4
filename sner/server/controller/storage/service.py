# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller service
"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import desc, func
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.controller.auth import role_required
from sner.server.controller.storage import blueprint
from sner.server.form import ButtonForm
from sner.server.form.storage import ServiceForm
from sner.server.model.storage import Host, Service
from sner.server.sqlafilter import filter_parser


VIZPORTS_LOW = 10.0
VIZPORTS_HIGH = 100.0


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
        ColumnDT(Service.comment, mData='comment'),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
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
    form = ServiceForm(obj=service)

    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=service.host_id))

    return render_template('storage/service/addedit.html', form=form, host=service.host)


@blueprint.route('/service/delete/<service_id>', methods=['GET', 'POST'])
@role_required('operator')
def service_delete_route(service_id):
    """delete service"""

    service = Service.query.get(service_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(service)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=service.host_id))

    return render_template('button-delete.html', form=form)


@blueprint.route('/service/vizports')
@role_required('operator')
def service_vizports_route():
    """visualize portmap"""

    query = db.session.query(Service.state, func.count(Service.id).label('state_count')).group_by(Service.state).order_by(desc('state_count'))
    portstates = [tmp for tmp in query.all()]

    query = db.session.query(Service.port, func.count(Service.id)).order_by(Service.port).group_by(Service.port)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)
    portmap = [{'port': port, 'count': count} for port, count in query.all()]
    # compute sizing for rendered element
    lowest = min(portmap, key=lambda x: x['count'])['count']
    highest = max(portmap, key=lambda x: x['count'])['count']
    coef = (VIZPORTS_HIGH-VIZPORTS_LOW) / max(1, (highest-lowest))
    for tmp in portmap:
        tmp['size'] = VIZPORTS_LOW + ((tmp['count']-lowest)*coef)

    return render_template('storage/service/vizports.html', portmap=portmap, portstates=portstates)


@blueprint.route('/service/portstat/<port>')
@role_required('operator')
def service_portstat_route(port):
    """generate port statistics fragment"""

    stats = {}
    query = db.session.query(Service.proto, func.count(Service.id)).filter(Service.port == port).order_by(Service.proto).group_by(Service.proto)
    for proto, count in query.all():
        stats[proto] = count
    infos = db.session.query(func.distinct(Service.info)).filter(Service.port == port, Service.info != '').all()
    comments = db.session.query(func.distinct(Service.comment)).filter(Service.port == port, Service.comment != '').all()
    hosts = db.session \
        .query(func.concat(Host.address, ' (', Host.hostname, ')'), Host.id) \
        .select_from(Service).outerjoin(Host) \
        .filter(Service.port == port).all()

    return render_template('storage/service/portstat.html', port=port, stats=stats, infos=infos, hosts=hosts, comments=comments)
