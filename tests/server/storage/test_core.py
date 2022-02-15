# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.core functions tests
"""

from sner.server.storage.core import get_related_models, StorageManager
from sner.server.storage.models import Host, Note, Service, Vuln


def test_get_related_models(app, service):  # pylint: disable=unused-argument
    """test function used to link new vuln/note to corresponding models"""

    thost, tservice = get_related_models('host', service.host_id)
    assert thost.id == service.host_id
    assert not tservice

    thost, tservice = get_related_models('service', service.id)
    assert thost.id == service.host_id
    assert tservice.id == service.id


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
