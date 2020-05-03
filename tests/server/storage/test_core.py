# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.core functions tests
"""

from sner.server.storage.core import get_related_models


def test_get_related_models(app, service):  # pylint: disable=unused-argument
    """test function used to link new vuln/note to corresponding models"""

    thost, tservice = get_related_models('host', service.host_id)
    assert thost.id == service.host_id
    assert not tservice

    thost, tservice = get_related_models('service', service.id)
    assert thost.id == service.host_id
    assert tservice.id == service.id
