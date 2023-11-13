# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.versioninfo component
"""

from flask import url_for
from selenium.webdriver.common.by import By

from sner.server.storage.models import Versioninfo
from tests.selenium import dt_count_rows, dt_rendered
from tests.selenium.storage import (
    check_annotate,
    check_dt_toolbox_freetag,
    check_dt_toolbox_multiactions,
    check_dt_toolbox_select_rows,
)


def test_versioninfo_list_route(live_server, sl_operator, versioninfo):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.versioninfo_list_route', _external=True))
    dt_rendered(sl_operator, 'versioninfo_list_table', versioninfo.product)


def test_versioninfo_list_route_query_form(live_server, sl_operator, service, versioninfo_factory):  # pylint: disable=unused-argument
    """simple test query form"""

    versioninfo_factory.create(
        host_id=service.host.id,
        host_address=service.host.address,
        host_hostname=service.host.hostname,
        service_proto=service.proto,
        service_port=service.port,
        product='apache httpd',
        version='1.2'
    )

    expected_version = "1.2"

    sl_operator.get(url_for('storage.versioninfo_list_route', _external=True))
    dt_rendered(sl_operator, 'versioninfo_list_table', expected_version)
    assert dt_count_rows(sl_operator, "versioninfo_list_table") == 1

    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@name="product"]').send_keys('apache')
    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@name="versionspec"]').send_keys('>=1.2')
    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@type="submit"]').click()
    dt_rendered(sl_operator, 'versioninfo_list_table', expected_version)
    assert dt_count_rows(sl_operator, "versioninfo_list_table") == 1


def test_versioninfo_list_route_annotate(live_server, sl_operator, versioninfo):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.versioninfo_list_route', _external=True))
    dt_rendered(sl_operator, 'versioninfo_list_table', versioninfo.product)
    check_annotate(sl_operator, 'abutton_annotate_dt', versioninfo)


def test_versioninfo_list_route_selectrows(live_server, sl_operator, versioninfo_multiaction):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    check_dt_toolbox_select_rows(sl_operator, 'storage.versioninfo_list_route', 'versioninfo_list_table')


def test_versioninfo_list_route_dt_toolbox_multiactions(live_server, sl_operator, versioninfo_multiaction):  # pylint: disable=unused-argument
    """test versioninfos multiactions"""

    check_dt_toolbox_multiactions(sl_operator, 'storage.versioninfo_list_route', 'versioninfo_list_table', Versioninfo, test_delete=False)


def test_versioninfo_list_route_dt_toolbox_freetag(live_server, sl_operator, versioninfo_multiaction):  # pylint: disable=unused-argument
    """test dt freetag buttons"""

    check_dt_toolbox_freetag(sl_operator, 'storage.versioninfo_list_route', 'versioninfo_list_table', Versioninfo)
