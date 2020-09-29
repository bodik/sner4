# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.host component
"""

from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.extensions import db
from sner.server.storage.models import Host, Note, Service, Vuln
from tests.selenium import dt_inrow_delete, dt_rendered, webdriver_waituntil
from tests.selenium.storage import check_annotate, check_select_rows, check_service_endpoint_dropdown, check_vulns_multiactions


def switch_tab(sclnt, tab_name, dt_name, control_data):
    """switches host view tab and waits until dt is rendered"""

    sclnt.find_element_by_xpath('//ul[@id="host_view_tabs"]//a[contains(@class, "nav-link") and @href="#%s"]' % tab_name).click()
    webdriver_waituntil(sclnt, EC.visibility_of_element_located((By.ID, dt_name)))
    dt_rendered(sclnt, dt_name, control_data)


def test_host_list_route(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.host_list_route', _external=True))
    dt_rendered(sl_operator, 'host_list_table', host.comment)


def test_host_list_route_inrow_delete(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """delete host inrow button"""

    host_id = host.id
    db.session.expunge(host)

    sl_operator.get(url_for('storage.host_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'host_list_table')

    assert not Host.query.get(host_id)


def test_host_list_route_annotate(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.host_list_route', _external=True))
    dt_rendered(sl_operator, 'host_list_table', host.comment)
    check_annotate(sl_operator, 'abutton_annotate_dt', host)


def test_host_edit_route_addtag(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """addtag buttons test"""

    assert 'todo' not in host.tags

    sl_operator.get(url_for('storage.host_edit_route', host_id=host.id, _external=True))
    sl_operator.find_element_by_xpath('//a[contains(@class, "abutton_addtag") and text()="Todo"]').click()
    sl_operator.find_element_by_xpath('//form//input[@type="submit"]').click()

    db.session.refresh(host)
    assert 'todo' in Host.query.get(host.id).tags


def test_host_view_route_annotate(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """test host annotation from view route"""

    sl_operator.get(url_for('storage.host_view_route', host_id=host.id, _external=True))
    check_annotate(sl_operator, 'abutton_annotate_view', host)


def test_host_view_route_services_list_inrow_delete(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """host view tabbed services dt tests; render and inrow delete"""

    service_id = service.id
    db.session.expunge(service)

    sl_operator.get(url_for('storage.host_view_route', host_id=service.host_id, _external=True))
    switch_tab(sl_operator, 'services', 'host_view_service_table', service.comment)
    dt_inrow_delete(sl_operator, 'host_view_service_table')

    assert not Service.query.get(service_id)


def test_host_view_route_services_list_service_endpoint_dropdown(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """host view tabbed services; SE dropdown"""

    sl_operator.get(url_for('storage.host_view_route', host_id=service.host_id, _external=True))
    switch_tab(sl_operator, 'services', 'host_view_service_table', service.comment)
    check_service_endpoint_dropdown(sl_operator, sl_operator.find_element_by_id('host_view_service_table'), service.port)


def test_host_view_route_vulns_list_inrow_delete(live_server, sl_operator, vuln):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; render and inrow delete"""

    vuln_id = vuln.id
    db.session.expunge(vuln)

    sl_operator.get(url_for('storage.host_view_route', host_id=vuln.host_id, _external=True))
    switch_tab(sl_operator, 'vulns', 'host_view_vuln_table', vuln.comment)
    dt_inrow_delete(sl_operator, 'host_view_vuln_table')

    assert not Vuln.query.get(vuln_id)


def test_host_view_route_vulns_list_service_endpoint_dropdown(live_server, sl_operator, vuln_factory, service):  # pylint: disable=unused-argument
    """host view tabbed vulns; SE dropdown"""

    test_vuln = vuln_factory.create(service=service)

    sl_operator.get(url_for('storage.host_view_route', host_id=test_vuln.host_id, _external=True))
    switch_tab(sl_operator, 'vulns', 'host_view_vuln_table', test_vuln.comment)
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element_by_id('host_view_vuln_table'),
        f'{test_vuln.service.port}/{test_vuln.service.proto}'
    )


def test_host_view_route_vulns_list_selectrows(live_server, sl_operator, vulns_multiaction):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; selections"""

    sl_operator.get(url_for('storage.host_view_route', host_id=vulns_multiaction[0].host_id, _external=True))
    switch_tab(sl_operator, 'vulns', 'host_view_vuln_table', vulns_multiaction[-1].comment)
    check_select_rows(sl_operator, 'host_view_vuln_table')


def test_host_view_route_vulns_list_multiactions(live_server, sl_operator, vulns_multiaction):  # pylint: disable=unused-argument
    """host view tabbed vulns dt test; multiactions"""

    sl_operator.get(url_for('storage.host_view_route', host_id=vulns_multiaction[0].host_id, _external=True))
    switch_tab(sl_operator, 'vulns', 'host_view_vuln_table', vulns_multiaction[-1].comment)
    check_vulns_multiactions(sl_operator, 'host_view_vuln_table')


def test_host_view_route_notes_list_inrow_delete(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """host view tabbed notes dt test; render and inrow delete"""

    note_id = note.id
    db.session.expunge(note)

    sl_operator.get(url_for('storage.host_view_route', host_id=note.host_id, _external=True))
    switch_tab(sl_operator, 'notes', 'host_view_note_table', note.comment)
    dt_inrow_delete(sl_operator, 'host_view_note_table')

    assert not Note.query.get(note_id)


def test_host_view_route_notes_list_service_endpoint_dropdown(live_server, sl_operator, note_factory, service):  # pylint: disable=unused-argument
    """host view tabbed notes; SE dropdown"""

    test_note = note_factory.create(service=service)

    sl_operator.get(url_for('storage.host_view_route', host_id=test_note.host_id, _external=True))
    switch_tab(sl_operator, 'notes', 'host_view_note_table', test_note.comment)
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element_by_id('host_view_note_table'),
        f'{test_note.service.port}/{test_note.service.proto}'
    )
