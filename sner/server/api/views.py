# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 controller
"""

import binascii
from base64 import b64decode
from datetime import datetime, timedelta
from http import HTTPStatus

from flask import jsonify, Response
from flask_login import current_user
from flask_smorest import Blueprint
from sqlalchemy import func, or_
from sqlalchemy_filters import apply_filters

from sner.server.api.schema import (
    JobAssignArgsSchema,
    JobAssignmentSchema,
    JobOutputSchema,
    PublicHostArgsSchema,
    PublicHostSchema,
    PublicRangeArgsSchema,
    PublicRangeSchema,
    PublicServicelistArgsSchema,
    PublicServicelistSchema
)
from sner.server.auth.core import apikey_required
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SchedulerServiceBusyException
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.sqlafilter import FILTER_PARSER
from sner.server.storage.models import Host, Note, Service, Vuln


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/v2/scheduler/job/assign', methods=['POST'])
@apikey_required('agent')
@blueprint.arguments(JobAssignArgsSchema)
@blueprint.response(HTTPStatus.OK, JobAssignmentSchema)
def v2_scheduler_job_assign_route(args):
    """assign job for agent"""

    try:
        resp = SchedulerService.job_assign(args.get('queue'), args.get('caps', []))
    except SchedulerServiceBusyException:
        resp = {}  # nowork
    return resp


@blueprint.route('/v2/scheduler/job/output', methods=['POST'])
@apikey_required('agent')
@blueprint.arguments(JobOutputSchema)
def v2_scheduler_job_output_route(args):
    """receive output from assigned job"""

    try:
        output = b64decode(args['output'])
    except binascii.Error:
        return jsonify({'message': 'invalid request'}), HTTPStatus.BAD_REQUEST

    job = Job.query.filter(Job.id == args['id'], Job.retval == None).one_or_none()  # noqa: E711  pylint: disable=singleton-comparison
    if not job:
        # invalid/repeated requests are silently discarded, agent would delete working data
        # on it's side as well
        return jsonify({'message': 'discard job'})

    try:
        SchedulerService.job_output(job, args['retval'], output)
    except SchedulerServiceBusyException:
        return jsonify({'message': 'server busy'}), HTTPStatus.TOO_MANY_REQUESTS

    return jsonify({'message': 'success'})


@blueprint.route('/v2/stats/prometheus')
@blueprint.response(HTTPStatus.OK, {'type': 'string'}, content_type='text/plain')
def v2_stats_prometheus_route():
    """internal stats"""

    stats = {}

    stats['sner_storage_hosts_total'] = Host.query.count()
    stats['sner_storage_services_total'] = Service.query.count()
    stats['sner_storage_vulns_total'] = Vuln.query.count()
    stats['sner_storage_notes_total'] = Note.query.count()

    stale_horizont = datetime.utcnow() - timedelta(days=5)
    stats['sner_scheduler_jobs_total{state="running"}'] = Job.query.filter(Job.retval == None, Job.time_start > stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{state="stale"}'] = Job.query.filter(Job.retval == None, Job.time_start < stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    stats['sner_scheduler_jobs_total{state="finished"}'] = Job.query.filter(Job.retval == 0).count()
    stats['sner_scheduler_jobs_total{state="failed"}'] = Job.query.filter(Job.retval != 0).count()

    queue_targets = db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    for queue, targets in queue_targets:
        stats[f'sner_scheduler_queue_targets_total{{name="{queue}"}}'] = targets

    output = '\n'.join(f'{key} {val}' for key, val in stats.items())
    return Response(output, mimetype='text/plain')


@blueprint.route('/v2/public/storage/host')
@apikey_required('user')
@blueprint.arguments(PublicHostArgsSchema, location='query')
@blueprint.response(HTTPStatus.OK, PublicHostSchema)
def v2_public_storage_host_route(args):
    """host data by address"""

    if not current_user.api_networks:
        return None

    restrict = [Host.address.op('<<=')(net) for net in current_user.api_networks]
    query = Host.query.filter(Host.address == str(args['address'])).filter(or_(*restrict))

    host = query.one_or_none()
    if not host:
        return None

    # host.notes relation holds all notes regardless of it's link to service filter response model in order to cope with output schema
    # the desing breaks the normalzation, but allows to do simple queries for notes/vulns for with all parents attributes
    # notes.filter(Service.port=="443" OR Host.address=="78.128.214.40")
    # also https://hashrocket.com/blog/posts/modeling-polymorphic-associations-in-a-relational-database
    host_data = {
        **host.__dict__,
        'services': host.services,
        'notes': [note for note in host.notes if note.service_id is None]
    }
    return host_data


@blueprint.route('/v2/public/storage/range')
@apikey_required('user')
@blueprint.arguments(PublicRangeArgsSchema, location='query')
@blueprint.response(HTTPStatus.OK, PublicRangeSchema(many=True))
def v2_public_storage_range_route(args):
    """list of hosts by cidr with simplified data"""

    if not current_user.api_networks:
        return None

    restrict = [Host.address.op('<<=')(net) for net in current_user.api_networks]
    query = Host.query.filter(Host.address.op('<<=')(str(args['cidr']))).filter(or_(*restrict))
    return query.all()


@blueprint.route('/v2/public/storage/servicelist')
@apikey_required('user')
@blueprint.arguments(PublicServicelistArgsSchema, location='query')
@blueprint.response(HTTPStatus.OK, PublicServicelistSchema(many=True))
def v2_public_storage_servicelist_route(args):
    """filtered servicelist (see sner.server.sqlafilter for syntax)"""

    if not current_user.api_networks:
        return None

    restrict = [Host.address.op('<<=')(net) for net in current_user.api_networks]
    query = db.session.query().select_from(Service).outerjoin(Host).add_columns(
        Host.address,
        Host.hostname,
        Service.proto,
        Service.port,
        Service.state,
        Service.info
    ).filter(or_(*restrict))

    if 'filter' in args:
        query = apply_filters(query, FILTER_PARSER.parse(args['filter']), do_auto_join=False)

    return query.all()
