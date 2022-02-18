# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller plannertree
"""

from flask import jsonify, render_template

from sner.server.auth.core import role_required
from sner.server.planner.core import Planner, QueueHandler, Schedule, StorageLoader
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
    """planner workflow visualisation"""

    def node_by_name(name):
        return next(filter(lambda obj: obj.get('name') == name, nodes), None)

    nodes = []
    links = []
    planner = Planner()

    for idx, queue in enumerate(Queue.query.all(), 0):
        nodes.append({'id': idx, 'name': queue.name, 'color': 'gray'})

    for idx, (stage_name, stage) in enumerate(planner.stages.items(), len(nodes)):
        node = {'id': idx, 'name': stage_name, 'size': 15}
        if isinstance(stage, Schedule):
            node['color'] = 'violet'
        if isinstance(stage, StorageLoader):
            node['color'] = 'green'
        if isinstance(stage, QueueHandler):
            node['color'] = 'lightblue'
        nodes.append(node)

    for stage_name, stage in planner.stages.items():
        if isinstance(stage, QueueHandler):
            for queue in stage.queues:
                links.append({'source': node_by_name(stage_name)['id'], 'target': node_by_name(queue)['id']})

    stages_rev = {v: k for k, v in planner.stages.items()}
    for stage, deps in planner.get_wiring().items():
        for dep in deps:
            links.append({'source': node_by_name(stages_rev[stage])['id'], 'target': node_by_name(stages_rev[dep])['id']})

    return jsonify({'nodes': nodes, 'links': links})
