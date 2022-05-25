# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 controller
"""

import binascii
from base64 import b64decode
from datetime import datetime, timedelta
from http import HTTPStatus

from flask import Response
from flask_smorest import Blueprint
from sqlalchemy import func

from sner.server.api.schema import (
    JobAssignArgsSchema,
    JobAssignmentSchema,
    JobOutputSchema,
    PublicHostSchema,
)
from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SchedulerServiceBusyException
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/v2/scheduler/job/assign')
@role_required('agent', api=True)
@blueprint.arguments(JobAssignArgsSchema, location='query')
@blueprint.response(HTTPStatus.OK, JobAssignmentSchema)
def v2_scheduler_job_assign_route(args):
    """assign job for agent"""

    try:
        resp = SchedulerService.job_assign(args.get('queue'), args.get('caps', []))
    except SchedulerServiceBusyException:
        resp = {}  # nowork
    return resp


@blueprint.route('/v2/scheduler/job/output', methods=['POST'])
@role_required('agent', api=True)
@blueprint.arguments(JobOutputSchema)
def v2_scheduler_job_output_route(args):
    """receive output from assigned job"""

    try:
        output = b64decode(args['output'])
    except binascii.Error:
        return {'message': 'invalid request'}, HTTPStatus.BAD_REQUEST

    job = Job.query.filter(Job.id == args['id'], Job.retval == None).one_or_none()  # noqa: E711  pylint: disable=singleton-comparison
    if not job:
        # invalid/repeated requests are silently discarded, agent would delete working data
        # on it's side as well
        return {'message': 'discard job'}

    try:
        SchedulerService.job_output(job, args['retval'], output)
    except SchedulerServiceBusyException:
        return {'message': 'server busy'}, HTTPStatus.TOO_MANY_REQUESTS

    return {'message': 'success'}


@blueprint.route('/v2/stats/prometheus')
@blueprint.response(HTTPStatus.OK, {'type': 'string'}, content_type='text/plain')
def v2_stats_prometheus_route():
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


@blueprint.route('/v2/public/storage/host/<host_address>')
@role_required('agent', api=True)
@blueprint.response(HTTPStatus.OK, PublicHostSchema)
def v2_public_storage_host_route(host_address):
    """get host data by address"""

    return Host.query.filter(Host.address == host_address).one_or_none()
