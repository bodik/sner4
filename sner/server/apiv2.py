# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 controller
"""

import binascii
from base64 import b64decode
from datetime import datetime, timedelta
from http import HTTPStatus

from flask import Response
from flask_smorest import abort, Blueprint
from marshmallow import fields, INCLUDE, Schema, post_dump, validate
from sqlalchemy import func

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SchedulerServiceBusyException
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln


blueprint = Blueprint('apiv2', __name__)  # pylint: disable=invalid-name


class JobAssignRequestSchema(Schema):
    queue = fields.String()
    caps = fields.List(fields.String)


class JobAssignResponseConfigSchema(Schema):
    class Meta:
        unknown = INCLUDE
    module = fields.String(required=True)

    # allow uknown fields to be dumped
    # https://github.com/marshmallow-code/marshmallow/issues/1545
    @post_dump(pass_original=True)
    def keep_unknowns(self, output, orig, **kwargs):
        for key in orig:
            if key not in output:
                output[key] = orig[key]
        return output


class JobAssignResponseSchema(Schema):
    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    config = fields.Nested(JobAssignResponseConfigSchema, required=True)
    targets = fields.List(fields.String, required=True)


@blueprint.route('/scheduler/job/assign')
@blueprint.arguments(JobAssignRequestSchema, location='query')
@blueprint.response(HTTPStatus.OK, JobAssignResponseSchema)
@role_required('agent', api=True)
def scheduler_job_assign_route(args):
    """assign job for agent"""

    try:
        resp = SchedulerService.job_assign(args.get('queue'), args.get('caps', []))
    except SchedulerServiceBusyException:
        resp = {}  # nowork
    if resp and JobAssignResponseSchema().validate(resp):
        abort(HTTPStatus.BAD_REQUEST, message='server generated invalid assignment')
    return resp


class JobOutputSchema(Schema):
    id = fields.String(required=True, validate=validate.Regexp(r'^[a-f0-9\-]{36}$'))
    retval = fields.Integer()
    output = fields.String()


@blueprint.route('/scheduler/job/output', methods=['POST'])
@blueprint.arguments(JobOutputSchema)
@role_required('agent', api=True)
def scheduler_job_output_route(args):
    """receive output from assigned job"""

    try:
        output = b64decode(args['output'])
    except binascii.Error:
        abort(HTTPStatus.BAD_REQUEST, message='invalid request')

    job = Job.query.filter(Job.id == args['id'], Job.retval == None).one_or_none()  # noqa: E711  pylint: disable=singleton-comparison
    if not job:
        # invalid/repeated requests are silently discarded, agent would delete working data
        # on it's side as well
        return {'code': 200, 'status': 'invalid job'}

    try:
        SchedulerService.job_output(job, args['retval'], output)
    except SchedulerServiceBusyException:
        abort(HTTPStatus.TOO_MANY_REQUESTS, message='server busy')

    return {'code': 200, 'status': 'success'}


@blueprint.route('/stats/prometheus')
@blueprint.response(HTTPStatus.OK, {'type': 'string'}, content_type='text/plain')
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


class PublicHostQuerySchema(Schema):
    address = fields.IP(required=True)


class PublicHostSchema(Schema):
    address = fields.String(required=True)
    hostname = fields.String()
    os = fields.String()
    tags = fields.List(fields.String)
    comment = fields.String()
    created = fields.DateTime()
    modified = fields.DateTime()
    rescan_time = fields.DateTime()


@blueprint.route('/public/storage/host', methods=['POST'])
@blueprint.arguments(PublicHostQuerySchema)
@blueprint.response(HTTPStatus.OK, PublicHostSchema)
@role_required('agent', api=True)
def get_host(args):
    """get host data by address"""

    return Host.query.filter(Host.address == str(args['address'])).one_or_none()
