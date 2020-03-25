# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium storage ui tests shared functions
"""

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.storage.models import Vuln
from tests.selenium import dt_wait_processing, no_ajax_pending, webdriver_waituntil


def check_select_rows(sclnt, dt_id):
    """check first-cols and toolbar button selections; there must be exactly 2 rows in the tested table"""

    # there should be two rows in total
    dt_elem = dt_wait_processing(sclnt, dt_id)
    toolbar_elem = sclnt.find_element_by_id('%s_toolbar' % dt_id)
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


def check_vulns_multiactions(sclnt, dt_id):
    """check vuln toolbar actions; there must be 2 rows to perform the test"""

    # there should be two rows in total
    dt_elem = dt_wait_processing(sclnt, dt_id)
    toolbar_elem = sclnt.find_element_by_id('%s_toolbar' % dt_id)
    assert len(dt_elem.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2

    # one cloud be be tagged
    dt_elem.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tag_multiid") and text()="Info"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert Vuln.query.filter(Vuln.name == 'vuln 1', Vuln.tags.any('info')).one()

    # or the other one
    dt_elem.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[2]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tag_multiid") and text()="Report"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert Vuln.query.filter(Vuln.name == 'vuln 2', Vuln.tags.any('report')).one()

    # both might be tagged at the same time
    toolbar_elem.find_element_by_xpath('//a[text()="All"]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_tag_multiid") and text()="Todo"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert Vuln.query.filter(Vuln.tags.any('todo')).count() == 2

    # or deleted
    toolbar_elem.find_element_by_xpath('//a[text()="All"]').click()
    toolbar_elem.find_element_by_xpath('//a[contains(@class, "abutton_delete_multiid")]').click()
    webdriver_waituntil(sclnt, EC.alert_is_present())
    sclnt.switch_to.alert.accept()
    dt_wait_processing(sclnt, dt_id)
    assert not Vuln.query.all()


def check_annotate(sclnt, annotate_elem_class, test_model):
    """check annotate functionality"""

    # disable fade, the timing interferes with the test
    sclnt.execute_script('$("div#modal-global").toggleClass("fade")')
    ActionChains(sclnt).double_click(sclnt.find_element_by_xpath('//td[contains(@class, "%s")]' % annotate_elem_class)).perform()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located((By.XPATH, '//h4[@class="modal-title" and text()="Annotate"]')))

    sclnt.find_element_by_css_selector('#modal-global form textarea[name="comment"]').send_keys('annotated comment')
    sclnt.find_element_by_css_selector('#modal-global form').submit()
    webdriver_waituntil(sclnt, EC.invisibility_of_element_located((By.XPATH, '//div[@class="modal-global"')))
    webdriver_waituntil(sclnt, no_ajax_pending())

    assert 'annotated comment' in test_model.__class__.query.get(test_model.id).comment
