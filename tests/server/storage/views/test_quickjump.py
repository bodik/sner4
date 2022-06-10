# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.jumper tests
"""

from http import HTTPStatus

from flask import url_for

from tests.server import get_csrf_token


def test_quickjump(cl_operator, host, service):
    """test quickjump"""

    data = {'quickjump': host.address, 'csrf_token': get_csrf_token(cl_operator)}
    response = cl_operator.post(url_for('storage.quickjump_route'), data)
    assert response.status_code == HTTPStatus.OK
    assert response.json['url'] == url_for('storage.host_view_route', host_id=host.id)

    data = {'quickjump': host.hostname, 'csrf_token': get_csrf_token(cl_operator)}
    response = cl_operator.post(url_for('storage.quickjump_route'), data)
    assert response.status_code == HTTPStatus.OK
    assert response.json['url'] == url_for('storage.host_view_route', host_id=host.id)

    data = {'quickjump': service.port, 'csrf_token': get_csrf_token(cl_operator)}
    response = cl_operator.post(url_for('storage.quickjump_route'), data)
    assert response.status_code == HTTPStatus.OK
    assert response.json['url'].startswith(f"{url_for('storage.service_list_route')}?filter=")
