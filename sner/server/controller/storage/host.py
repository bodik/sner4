"""controller host"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.controller import role_required
from sner.server.controller.storage import blueprint
from sner.server.form import ButtonForm
from sner.server.form.storage import HostForm
from sner.server.model.storage import Host, Note, Service, Vuln
from sner.server.sqlafilter import filter_parser


@blueprint.route('/host/list')
@role_required('operator')
def host_list_route():
    """list hosts"""

    return render_template('storage/host/list.html')


@blueprint.route('/host/list.json', methods=['GET', 'POST'])
@role_required('operator')
def host_list_json_route():
    """list hosts, data endpoint"""

    columns = [
        ColumnDT(Host.id, mData='id'),
        ColumnDT(Host.address, mData='address'),
        ColumnDT(Host.hostname, mData='hostname'),
        ColumnDT(Host.os, mData='os'),
        ColumnDT(func.count(func.distinct(Service.id)), mData='nr_svcs', global_search=False),
        ColumnDT(func.count(func.distinct(Vuln.id)), mData='nr_vulns', global_search=False),
        ColumnDT(func.count(func.distinct(Note.id)), mData='nr_notes', global_search=False),
        ColumnDT(Host.comment, mData='comment'),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Host) \
        .outerjoin(Service, Host.id == Service.host_id).outerjoin(Vuln, Host.id == Vuln.host_id).outerjoin(Note, Host.id == Note.host_id) \
        .group_by(Host.id)
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

    return render_template('storage/host/addedit.html', form=form, form_url=url_for('storage.host_add_route'))


@blueprint.route('/host/edit/<host_id>', methods=['GET', 'POST'])
@role_required('operator')
def host_edit_route(host_id):
    """edit host"""

    host = Host.query.get(host_id)
    form = HostForm(obj=host)

    if form.validate_on_submit():
        form.populate_obj(host)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=host.id))

    return render_template('storage/host/addedit.html', form=form, form_url=url_for('storage.host_edit_route', host_id=host_id))


@blueprint.route('/host/delete/<host_id>', methods=['GET', 'POST'])
@role_required('operator')
def host_delete_route(host_id):
    """delete host"""

    host = Host.query.get(host_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(host)
        db.session.commit()
        return redirect(url_for('storage.host_list_route'))

    return render_template('button-delete.html', form=form, form_url=url_for('storage.host_delete_route', host_id=host_id))


@blueprint.route('/host/vizdns')
@role_required('operator')
def host_vizdns_route():
    """dns hierarchy tree visualization"""

    crop = request.args.get('crop', 1, type=int)
    return render_template('storage/host/vizdns.html', crop=crop)


@blueprint.route('/host/vizdns.json')
@role_required('operator')
def host_vizdns_json_route():
    """dns hierarchy tree visualization data generator"""

    # from all hostnames we know, create tree structure dict-of-dicts
    def to_tree(node, items):
        if not items:
            return {}
        if items[0] not in node:
            node[items[0]] = {}
        node[items[0]] = to_tree(node[items[0]], items[1:])
        return node

    # walk through the tree and generate list of nodes and links
    def to_graph_data(parentid, treedata, nodes, links):
        for node in treedata:
            nodeid = len(nodes)
            nodes.append({'name': node, 'id': nodeid})
            if parentid is not None:
                links.append({'source': parentid, 'target': nodeid})
            (nodes, links) = to_graph_data(nodeid, treedata[node], nodes, links)
        return (nodes, links)

    crop = request.args.get('crop', 1, type=int)

    hostnames_tree = {}
    for ihost in Host.query.all():
        if ihost.hostname:
            tmp = list(reversed(ihost.hostname.split('.')[crop:]))
            if tmp:
                hostnames_tree = to_tree(hostnames_tree, ['DOTROOT']+tmp)

    (nodes, links) = to_graph_data(None, hostnames_tree, [], [])

    return jsonify({'nodes': nodes, 'links': links})


@blueprint.route('/host/view/<host_id>')
@role_required('operator')
def host_view_route(host_id):
    """view host"""

    host = Host.query.get(host_id)
    return render_template('storage/host/view.html', host=host, button_form=ButtonForm())
