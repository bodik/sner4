"""selenium ui tests for scheduler.queue component"""

from flask import url_for
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sner.server.model.scheduler import Queue
from tests.selenium import dt_inrow_delete, dt_rendered, dt_wait_processing, WEBDRIVER_WAIT


def test_queue_list_route(live_server, sl_operator, test_queue):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_rendered(sl_operator, 'queue_list_table', test_queue.name)


def test_queue_list_route_inrow_delete(live_server, sl_operator, test_queue):  # pylint: disable=unused-argument
    """delete queue inrow button"""

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'queue_list_table')
    assert not Queue.query.filter(Queue.id == test_queue.id).one_or_none()


def test_queue_list_route_inrow_flush(live_server, sl_operator, test_target):  # pylint: disable=unused-argument
    """flush queue inrow button"""

    dt_id = 'queue_list_table'

    sl_operator.get(url_for('scheduler.queue_list_route', _external=True))
    dt_wait_processing(sl_operator, dt_id)
    sl_operator.find_element_by_id(dt_id).find_element_by_class_name('abutton_queueflush_by_url').click()
    WebDriverWait(sl_operator, WEBDRIVER_WAIT).until(EC.alert_is_present())
    sl_operator.switch_to.alert.accept()
    dt_wait_processing(sl_operator, dt_id)
    assert not Queue.query.filter(Queue.id == test_target.queue_id).one_or_none().targets
