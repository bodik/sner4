# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller workflowtree
"""

import yaml
from flask import jsonify, render_template

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

    nodes = [{'id': 0, 'name': 'import', 'size': 20}]
    for idx, queue in enumerate(Queue.query.all(), 1):
        nodes.append({'id': idx, 'name': queue.name})

    links = []
    for queue in Queue.query.filter(Queue.workflow != None).all():   # noqa: E711  pylint: disable=singleton-comparison
        workflow = yaml.safe_load(queue.workflow)

        if workflow['step'] == 'import':
            links.append({'source': node_by_name(queue.name)['id'], 'target': node_by_name('import')['id']})

        elif workflow['step'].startswith('enqueue_'):
            target = node_by_name(workflow['queue'])
            if target:
                links.append({'source': node_by_name(queue.name)['id'], 'target': target['id']})

    return jsonify({'nodes': nodes, 'links': links})
