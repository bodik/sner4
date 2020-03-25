# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.views.login selenium tests
"""

from base64 import b64decode, b64encode

from fido2 import cbor
from flask import url_for

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.extensions import webauthn
from tests.server.auth import webauthn_device_init
from tests.selenium import webdriver_waituntil
from tests.selenium.auth import js_variable_ready


def test_login_webauthn(live_server, selenium, test_user):  # pylint: disable=unused-argument
    """test login by webauthn"""

    device = webauthn_device_init(test_user)

    selenium.get(url_for('auth.login_route', _external=True))
    selenium.find_element_by_xpath('//form//input[@name="username"]').send_keys(test_user.username)
    selenium.find_element_by_xpath('//form//input[@type="submit"]').click()

    # some javascript code must be emulated
    webdriver_waituntil(selenium, js_variable_ready('window.pkcro_raw'))
    pkcro = cbor.decode(b64decode(selenium.execute_script('return window.pkcro_raw;').encode('utf-8')))
    assertion = device.get(pkcro, 'https://%s' % webauthn.rp.id)
    selenium.execute_script(
        'authenticate_assertion(CBOR.decode(Sner.base64_to_array_buffer("%s")));' % b64encode(cbor.encode(assertion)).decode('utf-8'))
    # and back to standard test codeflow

    webdriver_waituntil(selenium, EC.presence_of_element_located((By.XPATH, '//a[text()="Logout"]')))
