# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.versioninfo component
"""

import json

from flask import url_for
from selenium.webdriver.common.by import By

from sner.server.storage.versioninfo import VersionInfoManager
from tests.selenium import dt_count_rows, dt_rendered


def test_versioninfo_list_route(live_server, sl_operator, versioninfo):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    expected_product = json.loads(versioninfo[0].data)["product"].lower()

    sl_operator.get(url_for('storage.versioninfo_list_route', _external=True))
    dt_rendered(sl_operator, 'versioninfo_list_table', expected_product)


def test_versioninfo_list_route_query_form(live_server, sl_operator, host, service_factory, note_factory):  # pylint: disable=unused-argument
    """simple test query form"""

    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=1),
        xtype='nmap.banner_dict',
        data='{"product": "Apache httpd", "version": "1.2"}'
    )
    note_factory.create(
        host=host,
        service=service_factory.create(host=host, port=2),
        xtype='nmap.banner_dict',
        data='{"product": "Apache httpd", "version": "3.14"}'
    )
    VersionInfoManager.rebuild()

    expected_version = "3.14"

    sl_operator.get(url_for('storage.versioninfo_list_route', _external=True))
    dt_rendered(sl_operator, 'versioninfo_list_table', expected_version)
    assert dt_count_rows(sl_operator, "versioninfo_list_table") == 2

    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@name="product"]').send_keys('apache')
    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@name="versionspec"]').send_keys('>=3.14')
    sl_operator.find_element(By.XPATH, '//form[@id="versioninfo_query_form"]//input[@type="submit"]').click()
    dt_rendered(sl_operator, 'versioninfo_list_table', expected_version)
    assert dt_count_rows(sl_operator, "versioninfo_list_table") == 1
