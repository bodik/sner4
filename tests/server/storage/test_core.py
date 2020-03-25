# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.core functions tests
"""

from sner.server.storage.core import get_related_models


def test_get_related_models(app, test_service):  # pylint: disable=unused-argument
    """test function used to link new vuln/note to corresponding models"""

    host, service = get_related_models('host', test_service.host_id)
    assert host.id == test_service.host_id
    assert not service

    host, service = get_related_models('service', test_service.id)
    assert host.id == test_service.host_id
    assert service.id == test_service.id
