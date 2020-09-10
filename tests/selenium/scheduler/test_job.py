# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for scheduler.job component
"""

import json

from flask import url_for
from selenium.webdriver.support import expected_conditions as EC

from sner.server.extensions import db
from sner.server.scheduler.models import Job, Target
from tests.selenium import dt_inrow_delete, dt_rendered, dt_wait_processing, webdriver_waituntil


def test_job_list_route(live_server, sl_operator, job):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.job_list_route', _external=True))
    dt_rendered(sl_operator, 'job_list_table', job.id)


def test_job_list_route_inrow_delete(live_server, sl_operator, job):  # pylint: disable=unused-argument
    """delete job inrow button"""

    job_id = job.id
    db.session.expunge(job)

    sl_operator.get(url_for('scheduler.job_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'job_list_table')
    assert not Job.query.get(job_id)


def test_job_list_route_inrow_repeat(live_server, sl_operator, job):  # pylint: disable=unused-argument
    """job list inrow  requeue button"""

    dt_id = 'job_list_table'
    sl_operator.get(url_for('scheduler.job_list_route', _external=True))
    dt_wait_processing(sl_operator, dt_id)
    sl_operator.find_element_by_id(dt_id).find_element_by_class_name('abutton_submit_dataurl_jobrepeat').click()
    webdriver_waituntil(sl_operator, EC.alert_is_present())
    sl_operator.switch_to.alert.accept()
    dt_wait_processing(sl_operator, dt_id)

    assert len(json.loads(job.assignment)['targets']) == Target.query.count()
