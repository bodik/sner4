# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests module
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


WEBDRIVER_WAIT = 10


class JsNoAjaxPending():  # pylint: disable=too-few-public-methods
    """custom expected_condition, wait for all ajax calls to finish"""

    def __call__(self, driver):
        return driver.execute_script('return(typeof(window.jQuery) === "function" && jQuery.active === 0)')


def webdriver_waituntil(sclnt, condition):
    """webdriver wait until shortcut"""
    return WebDriverWait(sclnt, WEBDRIVER_WAIT).until(condition)


def dt_wait_processing(sclnt, dt_id):
    """wait until all ajax finished and dt_id processing (hopefully) ended"""

    webdriver_waituntil(sclnt, JsNoAjaxPending())
    webdriver_waituntil(sclnt, EC.invisibility_of_element_located((By.ID, '%s_processing' % dt_id)))
    return sclnt.find_element_by_id(dt_id)


def dt_rendered(sclnt, dt_id, td_data):
    """test for td_data rendered in dt_id, eg. datatable rendered test data"""

    dt_wait_processing(sclnt, dt_id)
    assert sclnt.find_element_by_xpath('//table[@id="%s"]/tbody/tr/td[text()="%s"]' % (dt_id, td_data))


def dt_inrow_delete(sclnt, dt_id, index=0):
    """test delete row/item rendered in _buttons by default ajaxed datatables"""

    dt_wait_processing(sclnt, dt_id)
    sclnt.find_element_by_id(dt_id).find_elements_by_class_name('abutton_submit_dataurl_delete')[index].click()
    webdriver_waituntil(sclnt, EC.alert_is_present())
    sclnt.switch_to.alert.accept()
    dt_wait_processing(sclnt, dt_id)
