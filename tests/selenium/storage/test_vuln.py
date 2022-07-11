# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.vuln component
"""

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.storage.models import Vuln
from tests.selenium import dt_inrow_delete, dt_rendered, dt_wait_processing, webdriver_waituntil
from tests.selenium.storage import check_annotate, check_select_rows, check_service_endpoint_dropdown, check_vulns_multiactions


def check_vulns_filtering(sclnt, dt_id):
    """test vuln views filtering functions"""

    toolbar_id = f'{dt_id}_toolbar'

    # there should be 4 rows in total
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 4

    # one not tagged
    sclnt.find_element(By.ID, toolbar_id).find_element(By.XPATH, '//a[text()="Not tagged"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 1
    assert dt_elem.find_element(By.XPATH, '//td/a[text()="vuln 1"]')

    # three tagged
    sclnt.find_element(By.ID, toolbar_id).find_element(By.XPATH, '//a[text()="Tagged"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 3
    assert not dt_elem.find_elements(By.XPATH, '//td/a[text()="vuln 1"]')

    # two already reviewed
    sclnt.find_element(By.ID, toolbar_id).find_element(By.XPATH, '//a[text()="Exclude reviewed"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 2
    assert dt_elem.find_element(By.XPATH, '//td/a[text()="vuln 1"]')
    assert dt_elem.find_element(By.XPATH, '//td/a[text()="vuln 2"]')

    # one should go directly to report
    sclnt.find_element(By.ID, toolbar_id).find_element(By.XPATH, '//a[text()="Only Report"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 1
    assert dt_elem.find_element(By.XPATH, '//td/a[text()="vuln 4"]')

    # and user must be able to loose the filter
    sclnt.find_element(By.XPATH, '//a[text()="Unfilter"]').click()
    dt_elem = dt_wait_processing(sclnt, dt_id)
    assert len(dt_elem.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 4


def test_vuln_list_route(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_rendered(sl_operator, 'vuln_list_table', vuln.comment)


def test_vuln_list_route_inrow_delete(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """delete vuln inrow button"""

    vuln_id = vuln.id
    db.session.expunge(vuln)

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'vuln_list_table')

    assert not Vuln.query.get(vuln_id)


def test_vuln_list_route_annotate(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_rendered(sl_operator, 'vuln_list_table', vuln.comment)
    check_annotate(sl_operator, 'abutton_annotate_dt', vuln)


def test_vuln_list_route_selectrows(live_server, sl_operator, vulns_multiaction):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    check_select_rows(sl_operator, 'vuln_list_table')


def test_vuln_list_route_multiactions(live_server, sl_operator, vulns_multiaction):  # pylint: disable=unused-argument
    """test vulns multiactions"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    check_vulns_multiactions(sl_operator, 'vuln_list_table')


def test_vuln_list_route_filtering(live_server, sl_operator, vulns_filtering):  # pylint: disable=unused-argument
    """test list vulns view filtering features"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    check_vulns_filtering(sl_operator, 'vuln_list_table')


def test_vuln_list_route_service_endpoint_dropdown(live_server, sl_operator, vuln_factory, service):  # pylint: disable=unused-argument
    """service endpoint uris dropdown test"""

    test_vuln = vuln_factory.create(service=service)

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_rendered(sl_operator, 'vuln_list_table', test_vuln.comment)
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element(By.ID, 'vuln_list_table'),
        f'{test_vuln.service.port}/{test_vuln.service.proto}'
    )


def test_vuln_list_route_moredata_dropdown(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """moredata dropdown test"""

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_rendered(sl_operator, 'vuln_list_table', vuln.comment)
    sl_operator.find_element(By.ID, 'vuln_list_table').find_element(
        By.XPATH,
        './/div[contains(@class, "dropdown")]/a[@title="Show more data"]'
    ).click()
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((
        By.XPATH,
        '//table[@id="vuln_list_table"]//h6[text()="More data"]'
    )))


def test_vuln_list_route_viatarget_visibility_toggle(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """viatarget visibility toggle"""

    class JsDocumentReloaded():  # pylint: disable=too-few-public-methods
        """custom expected_condition, wait for document to be realoaded"""

        def __call__(self, driver):
            return driver.execute_script('return(document.readyState==="complete" && document.title!=="reload helper")')

    sl_operator.get(url_for('storage.vuln_list_route', _external=True))
    dt_rendered(sl_operator, 'vuln_list_table', vuln.comment)

    webdriver_waituntil(sl_operator, EC.invisibility_of_element_located((By.XPATH, '//th[contains(text(), "via_target")]')))
    sl_operator.execute_script('document.title="reload helper"')

    sl_operator.find_element(By.XPATH, '//li[contains(@class, "dropdown")]/a[@id="dropdownUser"]').click()
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((By.XPATH, '//a[contains(text(), "Toggle via_target")]')))
    sl_operator.find_element(By.XPATH, '//a[contains(text(), "Toggle via_target")]').click()
    webdriver_waituntil(sl_operator, EC.alert_is_present())
    sl_operator.switch_to.alert.accept()
    webdriver_waituntil(sl_operator, JsDocumentReloaded())
    dt_rendered(sl_operator, 'vuln_list_table', vuln.comment)

    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((By.XPATH, '//th[contains(text(), "via_target")]')))


def test_vuln_view_route_tagging(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """test vuln view tagging features"""

    assert 'info' not in vuln.tags

    sl_operator.get(url_for('storage.vuln_view_route', vuln_id=vuln.id, _external=True))
    sl_operator.find_element(By.XPATH, '//a[contains(@class, "abutton_tag_view") and text()="Info"]').click()
    webdriver_waituntil(
        sl_operator, EC.visibility_of_element_located((By.XPATH, '//span[contains(@class, "tag-badge") and contains(text(), "info")]'))
    )

    db.session.refresh(vuln)
    assert 'info' in Vuln.query.get(vuln.id).tags


def test_vuln_view_route_annotate(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """test vuln annotation from view route"""

    sl_operator.get(url_for('storage.vuln_view_route', vuln_id=vuln.id, _external=True))
    check_annotate(sl_operator, 'abutton_annotate_view', vuln)


def test_vuln_view_route_service_endpoint_dropdown(live_server, sl_operator, vuln_factory, service):  # pylint: disable=unused-argument
    """test note annotation from view route"""

    test_vuln = vuln_factory.create(service=service)

    sl_operator.get(url_for('storage.vuln_view_route', vuln_id=test_vuln.id, _external=True))
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element(By.XPATH, '//td[contains(@class, "service_endpoint_dropdown")]'),
        f'<Service {test_vuln.service.id}: {format_host_address(test_vuln.host.address)} {test_vuln.service.proto}.{test_vuln.service.port}>'
    )


def test_vuln_view_route_moredata_dropdown(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """test vuln view breadcrumb ribbon moredata dropdown"""

    sl_operator.get(url_for('storage.vuln_view_route', vuln_id=vuln.id, _external=True))
    sl_operator.find_element(By.XPATH, '//div[contains(@class, "breadcrumb-buttons")]').find_element(
        By.XPATH,
        './/div[contains(@class, "dropdown")]/a[@title="Show more data"]'
    ).click()
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((
        By.XPATH,
        '//div[contains(@class, "breadcrumb-buttons")]//h6[text()="More data"]'
    )))


def test_vuln_grouped_route(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """test grouped vulns view"""

    sl_operator.get(url_for('storage.vuln_grouped_route', _external=True))
    dt_wait_processing(sl_operator, 'vuln_grouped_table')
    assert len(sl_operator.find_elements(By.XPATH, '//tbody/tr[@role="row"]')) == 1


def test_vuln_grouped_route_filtering(live_server, sl_operator, vulns_filtering):  # pylint: disable=unused-argument
    """test grouped vulns view filtering features"""

    sl_operator.get(url_for('storage.vuln_grouped_route', _external=True))
    check_vulns_filtering(sl_operator, 'vuln_grouped_table')
