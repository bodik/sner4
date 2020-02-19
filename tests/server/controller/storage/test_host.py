# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
controller hosts tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.storage import Host
from tests.server.model.storage import create_test_host


def test_host_list_route(cl_operator):
    """host list route test"""

    response = cl_operator.get(url_for('storage.host_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_host_list_json_route(cl_operator, test_host):
    """host list_json route test"""

    response = cl_operator.post(url_for('storage.host_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_host.hostname})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['hostname'] == test_host.hostname

    response = cl_operator.post(
        url_for('storage.host_list_json_route', filter='Host.hostname=="%s"' % test_host.hostname),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['hostname'] == test_host.hostname


def test_host_add_route(cl_operator):
    """host add route test"""

    test_host = create_test_host()

    form = cl_operator.get(url_for('storage.host_add_route')).form
    form['address'] = test_host.address
    form['hostname'] = test_host.hostname
    form['os'] = test_host.os
    form['comment'] = test_host.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    host = Host.query.filter(Host.hostname == test_host.hostname).one_or_none()
    assert host
    assert host.hostname == test_host.hostname
    assert host.os == test_host.os
    assert host.comment == test_host.comment


def test_host_edit_route(cl_operator, test_host):
    """host edit route test"""

    form = cl_operator.get(url_for('storage.host_edit_route', host_id=test_host.id)).form
    form['hostname'] = 'edited-'+form['hostname'].value
    form['comment'] = ''
    form['return_url'] = url_for('storage.host_list_route')
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    host = Host.query.filter(Host.id == test_host.id).one_or_none()
    assert host
    assert host.hostname == form['hostname'].value
    assert host.comment is None


def test_host_delete_route(cl_operator, test_host):
    """host delete route test"""

    form = cl_operator.get(url_for('storage.host_delete_route', host_id=test_host.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    host = Host.query.filter(Host.id == test_host.id).one_or_none()
    assert not host


def test_host_vizdns_route(cl_operator):
    """host vizdns route test"""

    response = cl_operator.get(url_for('storage.host_vizdns_route'))
    assert response.status_code == HTTPStatus.OK


def test_host_vizdns_json_route(cl_operator, test_host):
    """host vizdns.json route test"""

    response = cl_operator.get(url_for('storage.host_vizdns_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert test_host.hostname.split('.')[0] in [tmp["name"] for tmp in response_data["nodes"]]


def test_host_view_route(cl_operator, test_host):
    """host view route test"""

    response = cl_operator.get(url_for('storage.host_view_route', host_id=test_host.id))
    assert response.status_code == HTTPStatus.OK
