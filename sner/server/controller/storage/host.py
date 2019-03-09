"""controller host"""

from flask import current_app, jsonify, redirect, render_template, request, url_for

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
from sner.server.model.storage import Host


@blueprint.route('/host/list')
def host_list_route():
	"""list hosts"""

	page = request.args.get('page', 1, type=int)
	hosts = Host.query.paginate(page, current_app.config['SNER_ITEMS_PER_PAGE'])
	return render_template('storage/host/list.html', hosts=hosts, generic_button_form=GenericButtonForm())


@blueprint.route('/host/delete/<host_id>', methods=['GET', 'POST'])
def host_delete_route(host_id):
	"""delete host"""

	host = Host.query.get(host_id)
	form = GenericButtonForm()
	if form.validate_on_submit():
		db.session.delete(host)
		db.session.commit()
		return redirect(url_for('storage.host_list_route'))
	return render_template('button_delete.html', form=form, form_url=url_for('storage.host_delete_route', host_id=host_id))


@blueprint.route('/host/vizdns')
def host_vizdns_route():
	crop = request.args.get('crop', 1, type=int)
	return render_template('storage/host/vizdns.html', crop=crop)


@blueprint.route('/host/vizdns.json')
def host_vizdns_json_route():

	## from all hostnames we know, create tree structure dict-of-dicts
	def to_tree(node, items):
		if not items:
			return {}
		if items[0] not in node:
			node[items[0]] = {}
		node[items[0]] = to_tree(node[items[0]], items[1:])
		return node

	## walk through the tree and generate list of nodes and links
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
			hostnames_tree = to_tree(hostnames_tree, list(reversed(ihost.hostname.split('.')[crop:])))

	(nodes, links) = to_graph_data(None, hostnames_tree, [], [])

	return jsonify({'nodes': nodes, 'links': links})
