# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for quickjump
"""

from flask import url_for

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tests.selenium import webdriver_waituntil


def test_quickjump_route_autocomplete(live_server, sl_operator, host):  # pylint: disable=unused-argument
    """quickjump test"""

    sl_operator.get(url_for('index_route', _external=True))

    sl_operator.find_element(By.XPATH, '//form[@id="storage_quickjump_form"]/input[@name="quickjump"]').send_keys(host.address[:2])
    elem_xpath = f'//ul[contains(@class, "ui-autocomplete")]/li/div[contains(., "{host.address}")]'
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((By.XPATH, elem_xpath)))

    elem = sl_operator.find_element(By.XPATH, elem_xpath).click()
    sl_operator.find_element(By.XPATH, '//form[@id="storage_quickjump_form"]').submit()
    webdriver_waituntil(sl_operator, EC.url_to_be(url_for('storage.host_view_route', host_id=host.id, _external=True)))
