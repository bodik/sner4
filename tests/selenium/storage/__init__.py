# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium storage ui tests shared functions
"""

from flask import url_for

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.extensions import db
from tests.selenium import dt_rendered, dt_wait_processing, JsNoAjaxPending, webdriver_waituntil


def check_dt_toolbox_select_rows(sclnt, route_name, dt_id, load_route=True):
    """check first-cols and toolbar button selections; there must be exactly 2 rows in the tested table"""

    if load_route:
        # in case of mai data tables, toggle visibility, load page and test
        # in host view vuln tab data table is page already prepared by callee
        sclnt.execute_script("window.sessionStorage.setItem('dt_toolboxes_visible', '\"true\"');")
        sclnt.get(url_for(route_name, _external=True))

    dt_elem = dt_wait_processing(sclnt, dt_id)
    toolbar_elem = sclnt.find_element(By.ID, f'{dt_id}_toolbar')

    # there should be two rows in total
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 2

    # user must be able to select only one
    dt_elem.find_element(By.XPATH, '(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"][contains(@class, "selected")]')) == 1

    # select all
    toolbar_elem.find_element(By.XPATH, './/a[text()="All"]').click()
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"][contains(@class, "selected")]')) == 2

    # or deselect any of them
    toolbar_elem.find_element(By.XPATH, './/a[text()="None"]').click()
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"][contains(@class, "selected")]')) == 0  # pylint: disable=len-as-condition


def check_dt_toolbox_multiactions(sclnt, route_name, dt_id, model_class, load_route=True):
    """check dt toolbar toolbox actions; there must be 2 rows to perform the test"""

    if load_route:
        # in case of mai data tables, toggle visibility, load page and test
        # in host view vuln tab data table is page already prepared by callee
        sclnt.execute_script("window.sessionStorage.setItem('dt_toolboxes_visible', '\"true\"');")
        sclnt.get(url_for(route_name, _external=True))

    # there should be two rows in total
    dt_elem = dt_wait_processing(sclnt, dt_id)
    toolbar_elem = sclnt.find_element(By.ID, f'{dt_id}_toolbar')

    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 2

    # one cloud be be tagged
    dt_elem.find_element(By.XPATH, '(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    toolbar_elem.find_element(By.XPATH, './/a[contains(@class, "abutton_tag_multiid") and text()="Todo"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert model_class.query.filter(model_class.comment == 'comment1', model_class.tags.any('todo')).one()

    # or the other one
    dt_elem.find_element(By.XPATH, '(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[2]').click()
    toolbar_elem.find_element(By.XPATH, './/a[contains(@class, "abutton_tag_multiid") and text()="Todo"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert model_class.query.filter(model_class.comment == 'comment2', model_class.tags.any('todo')).one()

    # test untagging
    toolbar_elem.find_element(By.XPATH, './/a[text()="All"]').click()
    toolbar_elem.find_element(By.XPATH, './/a[contains(@class, "dropdown-toggle") and @title="remove tag dropdown"]').click()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located(
        (By.XPATH, f'//div[@id="{dt_id}_toolbar"]//a[text()="Todo" and @title="remove tag todo"]'))
    )
    toolbar_elem.find_element(By.XPATH, './/a[contains(@class, "abutton_untag_multiid") and text()="Todo"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert model_class.query.filter(model_class.tags.any('todo')).count() == 0

    # or deleted
    toolbar_elem.find_element(By.XPATH, './/a[text()="All"]').click()
    toolbar_elem.find_element(By.XPATH, './/a[contains(@class, "abutton_delete_multiid")]').click()
    webdriver_waituntil(sclnt, EC.alert_is_present())
    sclnt.switch_to.alert.accept()
    dt_wait_processing(sclnt, dt_id)
    assert not model_class.query.all()


def check_annotate(sclnt, annotate_elem_class, test_model):
    """check annotate functionality"""

    # disable fade, the timing interferes with the test
    sclnt.execute_script('$("div#modal-global").toggleClass("fade")')
    ActionChains(sclnt).double_click(sclnt.find_element(By.XPATH, f'//td[contains(@class, "{annotate_elem_class}")]')).perform()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located((By.XPATH, '//h4[@class="modal-title" and text()="Annotate"]')))

    sclnt.find_element(By.CSS_SELECTOR, '#modal-global form textarea[name="comment"]').send_keys('annotated comment')
    sclnt.find_element(By.CSS_SELECTOR, '#modal-global form').submit()
    webdriver_waituntil(sclnt, EC.invisibility_of_element_located((By.XPATH, '//div[@class="modal-global"]')))
    webdriver_waituntil(sclnt, JsNoAjaxPending())

    db.session.refresh(test_model)
    assert 'annotated comment' in test_model.__class__.query.get(test_model.id).comment


def check_service_endpoint_dropdown(sclnt, parent_elem, dropdown_value):
    """check service endpoint_dropdown"""

    parent_elem.find_element(By.XPATH, f'//div[contains(@class, "dropdown")]/a[text()="{dropdown_value}"]').click()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located((By.XPATH, '//h6[text()="Service endpoint URIs"]')))


def check_dt_toolbox_visibility_toggle(sclnt, route_name, dt_id, model_factory):
    """datatables multiaction toolboxes visibility toggle"""

    class JsDocumentReloaded():  # pylint: disable=too-few-public-methods
        """custom expected_condition, wait for document to be realoaded"""

        def __call__(self, driver):
            return driver.execute_script('return(document.readyState==="complete" && document.title!=="reload helper")')

    test_model = model_factory.create(comment='render helper')
    toolbox_elem = (By.ID, f'{dt_id}_toolbox')
    toggle_elem = (By.XPATH, '//a[contains(text(), "Toggle DT toolboxes")]')

    sclnt.get(url_for(route_name, _external=True))
    dt_rendered(sclnt, dt_id, getattr(test_model, 'comment'))

    webdriver_waituntil(sclnt, EC.invisibility_of_element_located(toolbox_elem))
    sclnt.execute_script('document.title="reload helper"')

    sclnt.find_element(By.XPATH, '//li[contains(@class, "dropdown")]/a[@id="dropdownUser"]').click()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located(toggle_elem))
    sclnt.find_element(*toggle_elem).click()
    webdriver_waituntil(sclnt, EC.alert_is_present())
    sclnt.switch_to.alert.accept()
    webdriver_waituntil(sclnt, JsDocumentReloaded())
    dt_rendered(sclnt, dt_id, getattr(test_model, 'comment'))

    webdriver_waituntil(sclnt, EC.visibility_of_element_located(toolbox_elem))
