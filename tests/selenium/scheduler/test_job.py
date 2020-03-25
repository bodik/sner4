# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for scheduler.job component
"""

from flask import url_for

from sner.server.scheduler.models import Job
from tests.selenium import dt_inrow_delete, dt_rendered


def test_job_list_route(live_server, sl_operator, test_job):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.job_list_route', _external=True))
    dt_rendered(sl_operator, 'job_list_table', test_job.id)


def test_job_list_route_inrow_delete(live_server, sl_operator, test_job):  # pylint: disable=unused-argument
    """delete job inrow button"""

    sl_operator.get(url_for('scheduler.job_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'job_list_table')
    assert not Job.query.get(test_job.id)
