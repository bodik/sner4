# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for scheduler.queue component
"""

from flask import url_for
from selenium.webdriver.support import expected_conditions as EC

from sner.server.scheduler.models import Queue
from tests.selenium import dt_inrow_delete, dt_rendered, dt_wait_processing, webdriver_waituntil


def test_queue_list_route(live_server, sl_operator, test_queue):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_rendered(sl_operator, 'queue_list_table', test_queue.ident)


def test_queue_list_route_inrow_delete(live_server, sl_operator, test_queue):  # pylint: disable=unused-argument
    """delete queue inrow button"""

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'queue_list_table')
    assert not Queue.query.get(test_queue.id)


def test_queue_list_route_inrow_flush(live_server, sl_operator, test_target):  # pylint: disable=unused-argument
    """flush queue inrow button"""

    dt_id = 'queue_list_table'

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_wait_processing(sl_operator, dt_id)
    sl_operator.find_element_by_id(dt_id).find_element_by_class_name('abutton_submit_dataurl_queueflush').click()
    webdriver_waituntil(sl_operator, EC.alert_is_present())
    sl_operator.switch_to.alert.accept()
    dt_wait_processing(sl_operator, dt_id)
    assert not Queue.query.get(test_target.queue_id).targets
