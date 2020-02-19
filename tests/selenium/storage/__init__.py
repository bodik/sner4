# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium storage ui tests shared functions
"""

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sner.server.model.storage import Vuln
from tests.selenium import dt_wait_processing, WEBDRIVER_WAIT


def check_select_rows(selenium, dt_id):
    """check first-cols and toolbar button selections; there must be exactly 2 rows in the tested table"""

    # there should be two rows in total
    dt_elem = dt_wait_processing(selenium, dt_id)
    toolbar_elem = selenium.find_element_by_id('%s_toolbar' % dt_id)
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2

    # user must be able to select only one
    dt_elem.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 1

    # select all
    toolbar_elem.find_element_by_xpath('//a[text()="All"]').click()
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 2

    # or deselect any of them
    toolbar_elem.find_element_by_xpath('//a[text()="None"]').click()
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 0  # pylint: disable=len-as-condition


def check_vulns_multiactions(selenium, dt_id):
    """check vuln toolbar actions; there must be 2 rows to perform the test"""

    # there should be two rows in total
    dt_elem = dt_wait_processing(selenium, dt_id)
    toolbar_elem = selenium.find_element_by_id('%s_toolbar' % dt_id)
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2

    # one cloud be be tagged
    dt_elem.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tagmulti") and text()="Info"]').click()
    dt_elem = dt_wait_processing(selenium, dt_id)
    assert Vuln.query.filter(Vuln.name == 'vuln 1', Vuln.tags.any('info')).one_or_none()

    # or the other one
    dt_elem.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[2]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tagmulti") and text()="Report"]').click()
    dt_elem = dt_wait_processing(selenium, dt_id)
    assert Vuln.query.filter(Vuln.name == 'vuln 2', Vuln.tags.any('report')).one_or_none()

    # both might be tagged at the same time
    toolbar_elem.find_element_by_xpath('//a[text()="All"]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tagmulti") and text()="Todo"]').click()
    dt_elem = dt_wait_processing(selenium, dt_id)
    assert Vuln.query.filter(Vuln.tags.any('todo')).count() == 2

    # or deleted
    toolbar_elem.find_element_by_xpath('//a[text()="All"]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_deletemulti")]').click()
    WebDriverWait(selenium, WEBDRIVER_WAIT).until(EC.alert_is_present())
    selenium.switch_to.alert.accept()
    dt_wait_processing(selenium, dt_id)
    assert not Vuln.query.all()
