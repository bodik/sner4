# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.core functions tests
"""

import pytest

from sner.server.parser import ParsedItemsDb
from sner.server.storage.core import get_related_models, StorageManager, vuln_report
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln


def test_get_related_models(app, service):  # pylint: disable=unused-argument
    """test function used to link new vuln/note to corresponding models"""

    thost, tservice = get_related_models('host', service.host_id)
    assert thost.id == service.host_id
    assert not tservice

    thost, tservice = get_related_models('service', service.id)
    assert thost.id == service.host_id
    assert tservice.id == service.id


def test_importparsed(app):  # pylint: disable=unused-argument
    """test import parsed addtags"""

    pidb = ParsedItemsDb()
    pidb.upsert_vuln('192.0.2.1', 'name1', 'xtype1', 'tcp', 80, 'target1', severity=SeverityEnum.INFO, data='data1')
    pidb.upsert_note('192.0.2.1', 'xtype1', 'tcp', 80, 'target1', data='data1')

    StorageManager.import_parsed(pidb, ['testtag'])

    host = Host.query.filter(Host.address == '192.0.2.1').one()
    assert host.tags == ['testtag']
    assert host.services[0].tags == ['testtag']
    assert host.vulns[0].tags == ['testtag']
    assert host.notes[0].tags == ['testtag']


def test_storagecleanup(app, host_factory, service_factory, vuln_factory, note_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    # host1
    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    StorageManager.cleanup_storage()
    assert Host.query.count() == 0

    # host2
    host2 = host_factory.create(address='127.127.127.136', hostname=None, os=None, comment=None)
    note_factory.create(host=host2, xtype='hostnames', data='adata')
    StorageManager.cleanup_storage()
    assert Host.query.count() == 0
    assert Note.query.count() == 0

    # host3
    host3 = host_factory.create(address='127.127.127.135', os='identified')
    service3 = service_factory.create(host=host3, proto='tcp', port=1, state='filtered:reason')
    note_factory.create(host=host3, service=service3)
    vuln_factory.create(host=host3, service=service3)
    service4 = service_factory.create(host=host3, proto='tcp', port=1, state='open:reason')
    vuln_factory.create(host=host3)
    vuln_factory.create(host=host3, service=service4)

    StorageManager.cleanup_storage()
    assert Host.query.count() == 1
    assert Service.query.count() == 1
    assert Vuln.query.count() == 2
    assert Note.query.count() == 0


def test_vuln_report(app, host_factory, service_factory, vuln_factory):  # pylint: disable=unused-argument
    """test vuln_report"""

    # additional test data required for 'misc' test (eg. multiple endpoints having same vuln)
    vuln = vuln_factory.create()
    vuln_name = vuln.name

    host1 = host_factory.create(address='127.3.3.1', hostname='testhost2.testdomain.tests')
    host2 = host_factory.create(address='::127:3:3:2', hostname='testhost2.testdomain.tests')
    vuln_factory.create(host=host1, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='vuln on many hosts', xtype='x', severity=SeverityEnum.CRITICAL)
    vuln_factory.create(host=host2, name='trim test', xtype='x', severity=SeverityEnum.UNKNOWN, descr='A'*1001)

    aggregable_vuln_data = {
        'name': 'agg reportdata vuln',
        'xtype': 'y',
        'descr': 'agg reportdata vuln description',
        'tags': ['report:data', 'i:via_sner']
    }
    vuln_factory.create(host=host1, **aggregable_vuln_data)
    service2 = service_factory.create(host=host2)
    vuln2 = vuln_factory.create(host=host2, service=service2, **aggregable_vuln_data)

    output = vuln_report()

    assert f',"{vuln_name}",' in output
    assert ',"misc",' in output
    assert ',"TRIMMED",' in output
    assert '[::127:3:3:2]' in output
    assert f'## Data IP: {vuln2.host.address}, Proto: {vuln2.service.proto}, Port: {service2.port}, Hostname: {host2.hostname}' in output
    assert 'i:via_sner' not in output

    output = vuln_report(qfilter='Host.address == "127.3.3.1"', group_by_host=True)
    assert output

    with pytest.raises(ValueError):
        output = vuln_report(qfilter='invalid')
