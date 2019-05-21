"""controller hosts tests"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.storage import Host
from tests.server.model.storage import create_test_host


def test_host_list_route(client):
    """host list route test"""

    response = client.get(url_for('storage.host_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Hosts list' in response


def test_host_list_json_route(client, test_host):
    """host list_json route test"""

    response = client.post(url_for('storage.host_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_host.hostname})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data["data"][0]["hostname"] == test_host.hostname

    response = client.post(
        url_for('storage.host_list_json_route', filter='Host.hostname=="%s"' % test_host.hostname),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data["data"][0]["hostname"] == test_host.hostname


def test_host_add_route(client):
    """host add route test"""

    test_host = create_test_host()

    form = client.get(url_for('storage.host_add_route')).form
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


def test_host_edit_route(client, test_host):
    """host edit route test"""

    form = client.get(url_for('storage.host_edit_route', host_id=test_host.id)).form
    form['hostname'] = 'edited-'+form['hostname'].value
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    host = Host.query.filter(Host.id == test_host.id).one_or_none()
    assert host
    assert host.hostname == form['hostname'].value


def test_host_delete_route(client, test_host):
    """host delete route test"""

    form = client.get(url_for('storage.host_delete_route', host_id=test_host.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    host = Host.query.filter(Host.id == test_host.id).one_or_none()
    assert not host


def test_host_vizdns_route(client):
    """host vizdns route test"""

    response = client.get(url_for('storage.host_vizdns_route'))
    assert response.status_code == HTTPStatus.OK


def test_host_vizdns_json_route(client, test_host):
    """host vizdns.json route test"""

    response = client.get(url_for('storage.host_vizdns_json_route', crop=0))
    assert response.status_code == HTTPStatus.OK

    response_data = json.loads(response.body.decode('utf-8'))
    assert test_host.hostname.split('.')[0] in [tmp["name"] for tmp in response_data["nodes"]]


def test_host_view_route(client, test_host):
    """host view route test"""

    response = client.get(url_for('storage.host_view_route', host_id=test_host.id))
    assert response.status_code == HTTPStatus.OK

    assert 'Host %d: %s (%s)' % (test_host.id, test_host.address, test_host.hostname) in response
