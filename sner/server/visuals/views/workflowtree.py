# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller workflowtree
"""

from flask import current_app, jsonify, render_template

from sner.server.auth.core import role_required
from sner.server.scheduler.models import Queue
from sner.server.visuals.views import blueprint


@blueprint.route('/workflowtree')
@role_required('operator')
def workflowtree_route():
    """workflows visualization"""

    return render_template('visuals/workflowtree.html')


@blueprint.route('/workflowtree.json')
@role_required('operator')
def workflowtree_json_route():
    """workflows data generator"""

    def node_by_name(name):
        return next(filter(lambda obj: obj.get('name') == name, nodes), None)

    config = current_app.config['SNER_PLANNER']

    nodes = [{'id': 0, 'name': 'import_jobs', 'size': 20}]
    for idx, queue in enumerate(Queue.query.all(), 1):
        nodes.append({'id': idx, 'name': queue.name})

    links = []
    for qname in config.get('import_jobs', []):
        links.append({'source': node_by_name(qname)['id'], 'target': node_by_name('import_jobs')['id']})

    for qname, next_qname in config.get('enqueue_servicelist', []) + config.get('enqueue_hostlist', []):
        target = node_by_name(next_qname)
        if target:
            links.append({'source': node_by_name(qname)['id'], 'target': target['id']})

    return jsonify({'nodes': nodes, 'links': links})
