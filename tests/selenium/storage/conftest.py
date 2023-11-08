# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared fixtures for storage component
"""

import pytest

from sner.server.storage.models import SeverityEnum


@pytest.fixture
def hosts_multiaction(host_factory):
    """prepare hosts for multiple selection and actions tests"""

    yield [
        host_factory.create(address='127.0.0.3', comment='comment1'),
        host_factory.create(address='127.0.0.4', comment='comment2'),
    ]


@pytest.fixture
def services_multiaction(host, service_factory):
    """prepare services for multiple selection and actions tests"""

    yield [
        service_factory.create(host=host, proto='tcp', port=1234, comment='comment1'),
        service_factory.create(host=host, proto='tcp', port=12345, comment='comment2')
    ]


@pytest.fixture
def vulns_multiaction(host, vuln_factory):
    """prepare vulns for multiple selection and actions tests"""

    yield [
        vuln_factory.create(host=host, name='vuln 1', xtype='test.123', severity=SeverityEnum.INFO, comment='comment1'),
        vuln_factory.create(host=host, name='vuln 2', xtype='test.123', severity=SeverityEnum.INFO, comment='comment2')
    ]


@pytest.fixture
def vulns_filtering(host, vuln_factory):
    """prepare set of vulns needed for basic filtering tests"""

    yield [
        vuln_factory.create(host=host, name='vuln 1', xtype='test.123', severity=SeverityEnum.INFO, tags=None),
        vuln_factory.create(host=host, name='vuln 2', xtype='test.123', severity=SeverityEnum.INFO, tags=['tagx']),
        vuln_factory.create(host=host, name='vuln 3', xtype='test.123', severity=SeverityEnum.INFO, tags=['info']),
        vuln_factory.create(host=host, name='vuln 4', xtype='test.123', severity=SeverityEnum.INFO, tags=['report'])
    ]


@pytest.fixture
def notes_multiaction(host, note_factory):
    """prepare notes for multiple selection and actions tests"""

    yield [
        note_factory.create(host=host, xtype='test.1234', data='dummy', comment='comment1'),
        note_factory.create(host=host, xtype='test.12345', data='dummy', comment='comment2'),
    ]


@pytest.fixture
def vulnsearch_multiaction(service, vulnsearch_factory):
    """prepare vulnsearch for multiple selection and actions tests"""

    yield [
        vulnsearch_factory.create(
            host_id=service.host.id,
            service_id=service.id,
            host_address=service.host.address,
            service_proto=service.proto,
            service_port=service.port,
            cveid='CVE-1990-0003',
            comment='comment1'
        ),
        vulnsearch_factory.create(
            host_id=service.host.id,
            service_id=service.id,
            host_address=service.host.address,
            service_proto=service.proto,
            service_port=service.port,
            cveid='CVE-1990-0004',
            comment='comment2'
        ),
    ]
