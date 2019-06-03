"""shared fixtures for storage component"""

import pytest

from sner.server.model.storage import SeverityEnum, Vuln
from tests import persist_and_detach


@pytest.fixture
def test_vulns_multiaction(test_host):
    """prepare vulns for multiple selection and actions tests"""

    yield [
        persist_and_detach(Vuln(host=test_host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, comment='comment1')),
        persist_and_detach(Vuln(host=test_host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, comment='comment2'))]


@pytest.fixture
def test_vulns_filtering(test_host):
    """prepare set of vulns needed for basic filtering tests"""

    yield [
        persist_and_detach(Vuln(host=test_host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, tags=None)),
        persist_and_detach(Vuln(host=test_host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, tags=['tagx'])),
        persist_and_detach(Vuln(host=test_host, name='vuln 3', xtype='test.123', severity=SeverityEnum.info, tags=['info'])),
        persist_and_detach(Vuln(host=test_host, name='vuln 4', xtype='test.123', severity=SeverityEnum.info, tags=['report']))]
