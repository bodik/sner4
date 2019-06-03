"""selenium ui tests module"""

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


WEBDRIVER_WAIT = 10


class no_ajax_pending():  # pylint: disable=invalid-name,too-few-public-methods
    """custom expected_condition, wait for all ajax calls to finish"""

    def __call__(self, driver):
        return driver.execute_script('return(typeof(window.jQuery) === "function" && jQuery.active === 0)')


def dt_wait_processing(selenium, dt_id):
    """wait until all ajax finished and dt_id processing (hopefully) ended"""

    WebDriverWait(selenium, WEBDRIVER_WAIT).until(no_ajax_pending())
    WebDriverWait(selenium, WEBDRIVER_WAIT).until(EC.invisibility_of_element_located((By.ID, '%s_processing' % dt_id)))


def dt_rendered(selenium, route, dt_id, td_data):
    """test for td_data rendered on route inside datatable dt_id, eg. datatable rendered test data"""

    selenium.get(url_for(route, _external=True))
    dt_wait_processing(selenium, dt_id)
    assert selenium.find_element_by_xpath('//table[@id="%s"]//tr[contains(@role, "row")]/td[text()="%s"]' % (dt_id, td_data))


def dt_inrow_delete(selenium, list_route, dt_id):
    """test delete row/item rendered in _buttons by default ajaxed datatables"""

    selenium.get(url_for(list_route, _external=True))
    dt_wait_processing(selenium, dt_id)
    elem = selenium.find_element_by_id(dt_id).find_element_by_class_name('abutton_delete_by_url')

    elem.click()
    WebDriverWait(selenium, WEBDRIVER_WAIT).until(EC.alert_is_present())
    selenium.switch_to.alert.accept()
    dt_wait_processing(selenium, dt_id)
