# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared fixtures for storage component
"""

import pytest

from sner.server.storage.models import SeverityEnum, Vuln
from tests import persist_and_detach


@pytest.fixture
def test_vulns_multiaction(test_host):
    """prepare vulns for multiple selection and actions tests"""

    yield list(map(persist_and_detach, [
        Vuln(host=test_host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, comment='comment1'),
        Vuln(host=test_host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, comment='comment2')]))


@pytest.fixture
def test_vulns_filtering(test_host):
    """prepare set of vulns needed for basic filtering tests"""

    yield list(map(persist_and_detach, [
        Vuln(host=test_host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, tags=None),
        Vuln(host=test_host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, tags=['tagx']),
        Vuln(host=test_host, name='vuln 3', xtype='test.123', severity=SeverityEnum.info, tags=['info']),
        Vuln(host=test_host, name='vuln 4', xtype='test.123', severity=SeverityEnum.info, tags=['report'])]))
