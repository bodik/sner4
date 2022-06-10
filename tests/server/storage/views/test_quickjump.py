# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.jumper tests
"""

from http import HTTPStatus

from flask import url_for

from tests.server import get_csrf_token


def test_quickjump_route(cl_operator, host, service):
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

    data = {'quickjump': 'notfound', 'csrf_token': get_csrf_token(cl_operator)}
    response = cl_operator.post(url_for('storage.quickjump_route'), data, status='*')
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = cl_operator.post(url_for('storage.quickjump_route'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_quickjump_autocomplete_route(cl_operator, host):
    """test quickjump autocomplete"""

    response = cl_operator.get(url_for('storage.quickjump_autocomplete_route'))
    assert not response.json

    response = cl_operator.get(url_for('storage.quickjump_autocomplete_route', term=host.address[:2]))
    assert host.address in response.json

    response = cl_operator.get(url_for('storage.quickjump_autocomplete_route', term=host.hostname[:2]))
    assert host.hostname in response.json
