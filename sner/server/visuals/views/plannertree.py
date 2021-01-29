# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller plannertree
"""

from flask import current_app, jsonify, render_template

from sner.server.auth.core import role_required
from sner.server.scheduler.models import Queue
from sner.server.visuals.views import blueprint


@blueprint.route('/plannertree')
@role_required('operator')
def plannertree_route():
    """planner pipelines/workflows visualization"""

    return render_template('visuals/plannertree.html')


@blueprint.route('/plannertree.json')
@role_required('operator')
def plannertree_json_route():
    """planner pipelines/workflows data generator"""

    def node_by_name(name):
        return next(filter(lambda obj: obj.get('name') == name, nodes), None)

    nodes = [{'id': 0, 'name': 'import_jobs', 'size': 20}]
    for idx, queue in enumerate(Queue.query.all(), 1):
        nodes.append({'id': idx, 'name': queue.name})

    config = current_app.config['SNER_PLANNER']
    links = []

    for pipeline in config['pipelines']:
        source_queue = None
        for step in pipeline['steps']:
            if step['step'] == 'load_job':
                source_queue = node_by_name(step['queue'])
                continue

            if (step['step'] == 'import_job') and source_queue:
                links.append({'source': source_queue['id'], 'target': node_by_name('import_jobs')['id']})
                continue

            if (step['step'] == 'enqueue') and source_queue:
                links.append({'source': source_queue['id'], 'target': node_by_name(step['queue'])['id']})
                continue

    return jsonify({'nodes': nodes, 'links': links})
