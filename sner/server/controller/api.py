# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api controller; only a stubs for binding routes implementations to application uri space
"""

from flask import Blueprint

from sner.server.controller.auth import role_required
from sner.server.controller.scheduler.job import job_assign_route, job_output_route


blueprint = Blueprint('api', __name__)  # pylint: disable=invalid-name


@blueprint.route('/v1/scheduler/job/assign')
@blueprint.route('/v1/scheduler/job/assign/<queue_id>')
@role_required('agent', api=True)
def v1_scheduler_job_assign_route(queue_id=None):
    """scheduler job assign stub"""
    return job_assign_route(queue_id)


@blueprint.route('/v1/scheduler/job/output', methods=['POST'])
@role_required('agent', api=True)
def v1_scheduler_job_output_route():
    """scheduler job output stub"""
    return job_output_route()
