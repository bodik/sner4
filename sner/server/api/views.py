# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
apiv2 controller
"""

import binascii
from base64 import b64decode
from http import HTTPStatus

from flask import current_app, jsonify, Response
from flask_login import current_user
from flask_smorest import Blueprint
from sqlalchemy import or_

import sner.server.api.schema as api_schema
from sner.server.api.core import get_metrics
from sner.server.auth.core import apikey_required
from sner.server.extensions import db
from sner.server.scheduler.core import SchedulerService, SchedulerServiceBusyException
from sner.server.scheduler.models import Job
from sner.server.storage.models import Host, Note, Service, VersionInfo, Vulnsearch
from sner.server.storage.version_parser import is_in_version_range, parse as versionspec_parse
from sner.server.utils import filter_query


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/v2/scheduler/job/assign', methods=['POST'])
@apikey_required('agent')
@blueprint.arguments(api_schema.JobAssignArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.JobAssignmentSchema)
def v2_scheduler_job_assign_route(args):
    """assign job for agent"""

    if current_app.config['SNER_MAINTENANCE']:
        return {}  # nowork

    try:
        resp = SchedulerService.job_assign(args.get('queue'), args.get('caps', []))
        if 'id' in resp:
            current_app.logger.info(f'api.scheduler job assign {resp.get("id")}')
    except SchedulerServiceBusyException:
        resp = {}  # nowork
    return resp


@blueprint.route('/v2/scheduler/job/output', methods=['POST'])
@apikey_required('agent')
@blueprint.arguments(api_schema.JobOutputSchema)
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
        job_id = job.id
        SchedulerService.job_output(job, args['retval'], output)
    except SchedulerServiceBusyException:
        return jsonify({'message': 'server busy'}), HTTPStatus.TOO_MANY_REQUESTS

    current_app.logger.info(f'api.scheduler job output {job_id}')
    return jsonify({'message': 'success'})


@blueprint.route('/v2/stats/prometheus')
@blueprint.response(HTTPStatus.OK, {'type': 'string'}, content_type='text/plain')
def v2_stats_prometheus_route():
    """internal stats"""

    return Response(get_metrics(), mimetype='text/plain')


@blueprint.route('/v2/public/storage/host', methods=['POST'])
@apikey_required('user')
@blueprint.arguments(api_schema.PublicHostArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicHostSchema)
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
    current_app.logger.info(f'api.public storage host {args}')
    return host_data


@blueprint.route('/v2/public/storage/range', methods=['POST'])
@apikey_required('user')
@blueprint.arguments(api_schema.PublicRangeArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicRangeSchema(many=True))
def v2_public_storage_range_route(args):
    """list of hosts by cidr with simplified data"""

    if not current_user.api_networks:
        return None

    restrict = [Host.address.op('<<=')(net) for net in current_user.api_networks]
    query = Host.query.filter(Host.address.op('<<=')(str(args['cidr']))).filter(or_(*restrict))
    current_app.logger.info(f'api.public storage range {args}')
    return query.all()


@blueprint.route('/v2/public/storage/servicelist', methods=['POST'])
@apikey_required('user')
@blueprint.arguments(api_schema.PublicServicelistArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicServicelistSchema(many=True))
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

    if not (query := filter_query(query, args.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    current_app.logger.info(f'api.public storage servicelist {args}')
    return query.all()


@blueprint.route("/v2/public/storage/notelist", methods=['POST'])
@apikey_required("user")
@blueprint.arguments(api_schema.PublicNotelistArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicNotelistSchema(many=True))
def v2_public_storage_notelist_route(args):
    """filtered notelist (see sner.server.sqlafilter for syntax)"""

    if not current_user.api_networks:
        return None

    restrict = [Host.address.op("<<=")(net) for net in current_user.api_networks]
    query = (
        db.session.query()
        .select_from(Note)
        .outerjoin(Host, Note.host_id == Host.id)
        .outerjoin(Service, Note.service_id == Service.id)
        .add_columns(
            Host.address,
            Host.hostname,
            Service.proto,
            Service.port,
            Note.via_target,
            Note.xtype,
            Note.data,
            Note.tags,
            Note.comment,
            Note.created,
            Note.modified,
            Note.import_time,
        )
        .filter(or_(*restrict))
    )

    if not (query := filter_query(query, args.get("filter"))):
        return jsonify({"message": "Failed to filter query"}), HTTPStatus.BAD_REQUEST

    current_app.logger.info(f"api.public storage notelist {args}")
    return query.all()


@blueprint.route("/v2/public/storage/versioninfo", methods=["POST"])
@apikey_required("user")
@blueprint.arguments(api_schema.PublicVersionInfoArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicVersionInfoSchema(many=True))
def v2_public_storage_versioninfo_route(args):
    """simple version search"""

    if not current_user.api_networks:
        return None

    restrict = [VersionInfo.host_address.op("<<=")(net) for net in current_user.api_networks]
    query = VersionInfo.query.filter(or_(*restrict))

    if not (query := filter_query(query, args.get("filter"))):
        return jsonify({"message": "Failed to filter query"}), HTTPStatus.BAD_REQUEST

    if "product" in args:
        query = query.filter(VersionInfo.product.ilike(f'%{args["product"]}%'))

    data = query.all()

    if "versionspec" in args:
        parsed_version_specifier = versionspec_parse(args["versionspec"])
        data = list(filter(
            lambda item: is_in_version_range(item.version, parsed_version_specifier),
            data
        ))

    current_app.logger.info(f"api.public storage versioninfo {args}")
    return data


@blueprint.route("/v2/public/storage/vulnsearch", methods=["POST"])
@apikey_required("user")
@blueprint.arguments(api_schema.PublicVulnsearchArgsSchema)
@blueprint.response(HTTPStatus.OK, api_schema.PublicVulnsearchSchema(many=True))
def v2_public_storage_vulnsearch_route(args):
    """simple vulnsearch search (see sner.server.sqlafilter for syntax)"""

    if not current_user.api_networks:
        return None

    restrict = [Vulnsearch.host_address.op("<<=")(net) for net in current_user.api_networks]
    query = Vulnsearch.query.filter(or_(*restrict))

    if not (query := filter_query(query, args.get("filter"))):
        return jsonify({"message": "Failed to filter query"}), HTTPStatus.BAD_REQUEST

    current_app.logger.info(f"api.public storage vulnsearch {args}")
    return query.all()
