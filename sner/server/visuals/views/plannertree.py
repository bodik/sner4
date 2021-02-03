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
    """planner pipelines simple (and incomplete) visualisation"""

    def node_by_name(name):
        return next(filter(lambda obj: obj.get('name') == name, nodes), None)

    def analyze_steps(ctx, steps):
        for step in steps:
            process_step(ctx, step)

    def process_step(ctx, step):
        if step['step'] == 'load_job':
            ctx['source_queue'] = node_by_name(step['queue'])

        if (step['step'] == 'import_job') and ctx.get('source_queue'):
            ctx['links'].append({'source': ctx['source_queue']['id'], 'target': node_by_name('import_jobs')['id']})

        if (step['step'] == 'enqueue') and ctx.get('source_queue'):
            ctx['links'].append({'source': ctx['source_queue']['id'], 'target': node_by_name(step['queue'])['id']})

        if step['step'] == 'run_group':
            analyze_steps(ctx, current_app.config['SNER_PLANNER']['step_groups'][step['name']])

    pipelines = current_app.config['SNER_PLANNER']['pipelines']
    nodes = [{'id': 0, 'name': 'import_jobs', 'size': 20}]
    links = []

    for idx, queue in enumerate(Queue.query.all(), 1):
        nodes.append({'id': idx, 'name': queue.name})

    for pipeline in pipelines:
        ctx = {'source_queue': None, 'links': []}
        analyze_steps(ctx, pipeline['steps'])
        links += ctx['links']

    return jsonify({'nodes': nodes, 'links': links})
