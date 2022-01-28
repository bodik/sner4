# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api controller; only a stubs for binding routes implementations to application uri space
"""

from datetime import datetime, timedelta
from http import HTTPStatus

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import func

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.core import assignment_get, job_process_output
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/scheduler/job/assign')
@role_required('agent', api=True)
def scheduler_job_assign_route():
    """assign job for agent"""

    return jsonify(assignment_get(request.args.get('queue'), request.args.getlist('caps')))


@blueprint.route('/scheduler/job/output', methods=['POST'])
@role_required('agent', api=True)
def scheduler_job_output_route():
    """receive output from assigned job"""

    try:
        job_process_output(request.json)
        return '', HTTPStatus.OK
    except RuntimeError as exc:
        return jsonify({'title': exc.args[0]}), exc.args[1]


@blueprint.route('/stats/prometheus')
def stats_prometheus_route():
    """returns internal stats; prometheus"""

    stats = {}

    stats['sner_storage_hosts_total'] = Host.query.count()
    stats['sner_storage_services_total'] = Service.query.count()
    stats['sner_storage_vulns_total'] = Vuln.query.count()
    stats['sner_storage_notes_total'] = Note.query.count()

    stale_horizont = datetime.utcnow() - timedelta(days=5)
    stats['sner_scheduler_jobs_total{{state="running"}}'] = Job.query.filter(Job.retval == None, Job.time_start > stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{{state="stale"}}'] = Job.query.filter(Job.retval == None, Job.time_start < stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{{state="finished"}}'] = Job.query.filter(Job.retval == 0).count()
    stats['sner_scheduler_jobs_total{{state="failed"}}'] = Job.query.filter(Job.retval != 0).count()

    queue_targets = db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    for queue, targets in queue_targets:
        stats[f'sner_scheduler_queue_targets_total{{name="{queue}"}}'] = targets

    output = '\n'.join(f'{key} {val}' for key, val in stats.items())
    return Response(output, mimetype='text/plain')
