# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared fixtures for storage component
"""

import pytest

from sner.server.storage.models import SeverityEnum


@pytest.fixture
def vulns_multiaction(host, vuln_factory):
    """prepare vulns for multiple selection and actions tests"""

    yield [
        vuln_factory.create(host=host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, comment='comment1'),
        vuln_factory.create(host=host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, comment='comment2')
    ]


@pytest.fixture
def vulns_filtering(host, vuln_factory):
    """prepare set of vulns needed for basic filtering tests"""

    yield [
        vuln_factory.create(host=host, name='vuln 1', xtype='test.123', severity=SeverityEnum.info, tags=None),
        vuln_factory.create(host=host, name='vuln 2', xtype='test.123', severity=SeverityEnum.info, tags=['tagx']),
        vuln_factory.create(host=host, name='vuln 3', xtype='test.123', severity=SeverityEnum.info, tags=['info']),
        vuln_factory.create(host=host, name='vuln 4', xtype='test.123', severity=SeverityEnum.info, tags=['report'])
    ]
