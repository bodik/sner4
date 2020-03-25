# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared fixtures for selenium tests
"""

from uuid import uuid4

import pytest
from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.auth.models import User
from sner.server.extensions import db
from tests.selenium import webdriver_waituntil
from tests.server.auth.models import test_user  # noqa: F401  pylint: disable=unused-import
from tests.server.scheduler.models import test_excl_network, test_job, test_queue, test_target, test_task  # noqa: F401  pylint: disable=unused-import
from tests.server.storage.models import test_host, test_note, test_service, test_vuln  # noqa: F401  pylint: disable=unused-import


@pytest.fixture
def firefox_options(firefox_options):  # pylint: disable=redefined-outer-name
    """override firefox options"""

    firefox_options.headless = True
    return firefox_options


def selenium_in_roles(sclnt, roles):
    """create user role and login selenium to role(s)"""

    tmp_password = str(uuid4())
    tmp_user = User(username='pytest_user', password=tmp_password, active=True, roles=roles)
    db.session.add(tmp_user)
    db.session.commit()

    sclnt.get(url_for('auth.login_route', _external=True))
    sclnt.find_element_by_xpath('//form//input[@name="username"]').send_keys(tmp_user.username)
    sclnt.find_element_by_xpath('//form//input[@name="password"]').send_keys(tmp_password)
    sclnt.find_element_by_xpath('//form//input[@type="submit"]').click()
    webdriver_waituntil(sclnt, EC.presence_of_element_located((By.XPATH, '//a[text()="Logout"]')))

    return sclnt


@pytest.fixture
def sl_user(selenium):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role user"""

    yield selenium_in_roles(selenium, ['user'])


@pytest.fixture
def sl_operator(selenium):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role operator"""

    yield selenium_in_roles(selenium, ['user', 'operator'])


@pytest.fixture
def sl_admin(selenium):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role admin"""

    yield selenium_in_roles(selenium, ['user', 'operator', 'admin'])
