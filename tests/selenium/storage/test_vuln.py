"""selenium ui tests for storage.vuln component"""

from flask import url_for
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sner.server.model.storage import Host, SeverityEnum, Vuln
from tests import persist_and_detach
from tests.selenium import dt_inrow_delete, dt_rendered, dt_wait_processing, WEBDRIVER_WAIT


def check_vuln_filtering(selenium, base_route, dt_id):
    """test vuln views filtering functions"""

    test_host = Host(address='127.0.0.44', hostname='localhostx.localdomain')
    persist_and_detach(test_host)
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 1', xtype='test.123', severity=SeverityEnum.info, tags=None))
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 2', xtype='test.123', severity=SeverityEnum.info, tags=['tagx']))
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 3', xtype='test.123', severity=SeverityEnum.info, tags=['info']))
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 4', xtype='test.123', severity=SeverityEnum.info, tags=['report']))

    # there should be 4 rows in total
    selenium.get(url_for(base_route, _external=True))
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 4

    # one not tagged
    selenium.find_element_by_xpath('//a[text()="Not tagged"]').click()
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 1
    assert selenium.find_element_by_xpath('//td/a[text()="vuln grouped 1"]')

    # three tagged
    selenium.find_element_by_xpath('//a[text()="Tagged"]').click()
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 3
    assert not selenium.find_elements_by_xpath('//td/a[text()="vuln grouped 1"]')

    # two already reviewed
    selenium.find_element_by_xpath('//a[text()="Exclude reviewed"]').click()
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2
    assert selenium.find_element_by_xpath('//td/a[text()="vuln grouped 1"]')
    assert selenium.find_element_by_xpath('//td/a[text()="vuln grouped 2"]')

    # one should go directly to report
    selenium.find_element_by_xpath('//a[text()="Only Report"]').click()
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 1
    assert selenium.find_element_by_xpath('//td/a[text()="vuln grouped 4"]')

    # and user must be able to loose the filter
    elem = selenium.find_element_by_xpath('//a[text()="unfilter"]')
    elem.click()
    dt_wait_processing(selenium, dt_id)
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 4


def test_list(live_server, selenium, test_vuln):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    dt_rendered(selenium, 'storage.vuln_list_route', 'vuln_list_table', test_vuln.comment)


def test_list_inrow_delete(live_server, selenium, test_vuln):  # pylint: disable=unused-argument
    """delete vuln inrow button"""

    dt_inrow_delete(selenium, 'storage.vuln_list_route', 'vuln_list_table')
    assert not Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()


def test_list_selections(live_server, selenium, test_host):
    """test dt selection and selection buttons"""

    persist_and_detach(Vuln(host=test_host, name='vuln grouped 1', xtype='test.123', severity=SeverityEnum.info))
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 2', xtype='test.123', severity=SeverityEnum.info))

    selenium.get(url_for('storage.vuln_list_route', _external=True))
    dt_wait_processing(selenium, 'vuln_list_table')
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2

    selenium.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 1

    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[text()="All"]').click()
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 2

    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[text()="None"]').click()
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"][contains(@class, "selected")]')) == 0


def test_list_multiple_actions(live_server, selenium, test_host):
    """test tagging"""

    persist_and_detach(Vuln(host=test_host, name='vuln grouped 1', xtype='test.123', severity=SeverityEnum.info))
    persist_and_detach(Vuln(host=test_host, name='vuln grouped 2', xtype='test.123', severity=SeverityEnum.info))

    selenium.get(url_for('storage.vuln_list_route', _external=True))
    dt_wait_processing(selenium, 'vuln_list_table')
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 2

    selenium.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[1]').click()
    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[contains(text(), "Info")]').click()
    dt_wait_processing(selenium, 'vuln_list_table')
    assert Vuln.query.filter(Vuln.name == 'vuln grouped 1', Vuln.tags.any('info')).one_or_none()

    selenium.find_element_by_xpath('(//tr[@role="row"]/td[contains(@class, "select-checkbox")])[2]').click()
    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[contains(text(), "Report")]').click()
    dt_wait_processing(selenium, 'vuln_list_table')
    assert Vuln.query.filter(Vuln.name == 'vuln grouped 2', Vuln.tags.any('report')).one_or_none()

    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[text()="All"]').click()
    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[contains(text(), "TODO")]').click()
    dt_wait_processing(selenium, 'vuln_list_table')
    assert Vuln.query.filter(Vuln.tags.any('todo')).count() == 2

    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[text()="All"]').click()
    selenium.find_element_by_xpath('//div[@id="vuln_list_table_toolbar"]//a[contains(@class, "abutton_deletemulti")]').click()
    WebDriverWait(selenium, WEBDRIVER_WAIT).until(EC.alert_is_present())
    selenium.switch_to.alert.accept()
    dt_wait_processing(selenium, 'vuln_list_table')
    assert not Vuln.query.all()


def test_list_filtering(live_server, selenium):
    """test list vulns view filtering features"""

    check_vuln_filtering(selenium, 'storage.vuln_list_route', 'vuln_list_table')


def test_grouped(live_server, selenium, test_vuln):  # pylint: disable=unused-argument
    """test grouped vulns view"""

    selenium.get(url_for('storage.vuln_grouped_route', _external=True))
    dt_wait_processing(selenium, 'vuln_grouped_table')
    assert len(selenium.find_elements_by_xpath('//tbody/tr[@role="row"]')) == 1


def test_grouped_filtering(live_server, selenium):
    """test grouped vulns view filtering features"""

    check_vuln_filtering(selenium, 'storage.vuln_grouped_route', 'vuln_grouped_table')
