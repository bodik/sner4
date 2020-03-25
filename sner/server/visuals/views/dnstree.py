# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller dnstree
"""

from flask import jsonify, render_template, request

from sner.server.auth.core import role_required
from sner.server.storage.models import Host
from sner.server.visuals.views import blueprint


@blueprint.route('/dnstree')
@role_required('operator')
def dnstree_route():
    """dns hierarchy tree visualization"""

    return render_template('visuals/dnstree.html')


@blueprint.route('/dnstree.json')
@role_required('operator')
def dnstree_json_route():
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

    crop = request.args.get('crop', 0, type=int)
    hostnames_tree = {}
    for ihost in Host.query.all():
        if ihost.hostname:
            tmp = list(reversed(ihost.hostname.split('.')[crop:]))
            if tmp:
                hostnames_tree = to_tree(hostnames_tree, ['DOTROOT']+tmp)

    (nodes, links) = to_graph_data(None, hostnames_tree, [], [])

    return jsonify({'nodes': nodes, 'links': links})
