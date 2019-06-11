"""selenium ui tests for storage.host component"""

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sner.server.model.storage import Host, Note, Service, Vuln
from tests.selenium import dt_inrow_delete, dt_rendered, WEBDRIVER_WAIT
from tests.selenium.storage import check_select_rows, check_vulns_multiactions


def test_host_list_route(live_server, sl_operator, test_host):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.host_list_route', _external=True))
    dt_rendered(sl_operator, 'host_list_table', test_host.comment)


def test_host_list_route_inrow_delete(live_server, sl_operator, test_host):  # pylint: disable=unused-argument
    """delete host inrow button"""

    sl_operator.get(url_for('storage.host_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'host_list_table')
    assert not Host.query.filter(Host.id == test_host.id).one_or_none()


def test_host_view_route_services_list(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """host view tabbed services dt tests; render and inrow delete"""

    sl_operator.get(url_for('storage.host_view_route', host_id=test_service.host_id, _external=True))
    dt_rendered(sl_operator, 'host_view_service_table', test_service.comment)

    dt_inrow_delete(sl_operator, 'host_view_service_table')
    assert not Service.query.filter(Service.id == test_service.id).one_or_none()


def test_host_view_route_vulns_list(live_server, sl_operator, test_vuln):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; render and inrow delete"""

    sl_operator.get(url_for('storage.host_view_route', host_id=test_vuln.host_id, _external=True))
    sl_operator.find_element_by_xpath('//a[@role="tab" and text()="Vulns"]').click()
    WebDriverWait(sl_operator, WEBDRIVER_WAIT).until(EC.visibility_of_element_located((By.ID, 'host_view_vuln_table')))
    dt_rendered(sl_operator, 'host_view_vuln_table', test_vuln.comment)

    dt_inrow_delete(sl_operator, 'host_view_vuln_table')
    assert not Vuln.query.filter(Vuln.id == test_vuln.id).one_or_none()


def test_host_view_route_notes_list(live_server, sl_operator, test_note):  # pylint: disable=unused-argument
    """host view tabbed notes dt test; render and inrow delete"""

    sl_operator.get(url_for('storage.host_view_route', host_id=test_note.host_id, _external=True))
    sl_operator.find_element_by_xpath('//a[@role="tab" and text()="Notes"]').click()
    WebDriverWait(sl_operator, WEBDRIVER_WAIT).until(EC.visibility_of_element_located((By.ID, 'host_view_note_table')))
    dt_rendered(sl_operator, 'host_view_note_table', test_note.comment)

    dt_inrow_delete(sl_operator, 'host_view_note_table')
    assert not Note.query.filter(Note.id == test_note.id).one_or_none()


def test_host_view_route_vulns_list_selectrows(live_server, sl_operator, test_vulns_multiaction):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; selections"""

    sl_operator.get(url_for('storage.host_view_route', host_id=test_vulns_multiaction[0].host_id, _external=True))
    sl_operator.find_element_by_xpath('//a[@role="tab" and text()="Vulns"]').click()
    WebDriverWait(sl_operator, WEBDRIVER_WAIT).until(EC.visibility_of_element_located((By.ID, 'host_view_vuln_table')))
    dt_rendered(sl_operator, 'host_view_vuln_table', test_vulns_multiaction[-1].comment)

    check_select_rows(sl_operator, 'host_view_vuln_table')


def test_host_view_route_vulns_list_multiactions(live_server, sl_operator, test_vulns_multiaction):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; multiactions"""

    sl_operator.get(url_for('storage.host_view_route', host_id=test_vulns_multiaction[0].host_id, _external=True))
    sl_operator.find_element_by_xpath('//a[@role="tab" and text()="Vulns"]').click()
    WebDriverWait(sl_operator, WEBDRIVER_WAIT).until(EC.visibility_of_element_located((By.ID, 'host_view_vuln_table')))
    dt_rendered(sl_operator, 'host_view_vuln_table', test_vulns_multiaction[-1].comment)

    check_vulns_multiactions(sl_operator, 'host_view_vuln_table')
