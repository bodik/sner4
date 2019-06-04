"""selenium ui tests for scheduler.job component"""

from flask import url_for

from sner.server.model.scheduler import Job
from tests.selenium import dt_inrow_delete, dt_rendered


def test_job_list_route(live_server, selenium, test_job):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    selenium.get(url_for('scheduler.job_list_route', _external=True))
    dt_rendered(selenium, 'job_list_table', test_job.id)


def test_job_list_route_inrow_delete(live_server, selenium, test_job):  # pylint: disable=unused-argument
    """delete job inrow button"""

    selenium.get(url_for('scheduler.job_list_route', _external=True))
    dt_inrow_delete(selenium, 'job_list_table')
    assert not Job.query.filter(Job.id == test_job.id).one_or_none()
