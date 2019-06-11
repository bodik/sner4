"""shared fixtures for selenium tests"""

from uuid import uuid4

import pytest
from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from sner.server import db
from sner.server.model.auth import User
from tests.selenium import WEBDRIVER_WAIT
from tests.server.model.auth import test_user  # noqa: F401  pylint: disable=unused-import
from tests.server.model.scheduler import test_excl_network, test_job, test_queue, test_target, test_task  # noqa: F401  pylint: disable=unused-import
from tests.server.model.storage import test_host, test_note, test_service, test_vuln  # noqa: F401  pylint: disable=unused-import


@pytest.fixture
def firefox_options(firefox_options):  # pylint: disable=redefined-outer-name
    """override firefox options"""

    firefox_options.headless = True
    return firefox_options


def selenium_in_roles(selenium, roles):
    """create user role and login selenium to role(s)"""

    tmp_password = str(uuid4())
    tmp_user = User(username='pytest_user', password=tmp_password, active=True, roles=roles)
    db.session.add(tmp_user)
    db.session.commit()

    selenium.get(url_for('auth.login_route', _external=True))
    selenium.find_element_by_xpath('//form//input[@id="username"]').send_keys(tmp_user.username)
    selenium.find_element_by_xpath('//form//input[@id="password"]').send_keys(tmp_password)
    selenium.find_element_by_xpath('//form//button[@type="submit"]').click()
    WebDriverWait(selenium, WEBDRIVER_WAIT).until(EC.presence_of_element_located((By.XPATH, '//a[text()="Logout"]')))

    return selenium


@pytest.fixture
def sl_operator(selenium):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role operator"""

    yield selenium_in_roles(selenium, ['user', 'operator'])


@pytest.fixture
def sl_admin(selenium):  # pylint: disable=redefined-outer-name
    """yield client authenticated to role admin"""

    yield selenium_in_roles(selenium, ['user', 'operator', 'admin'])
