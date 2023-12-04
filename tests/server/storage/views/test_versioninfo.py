# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.versioninfo tests
"""

import json
from http import HTTPStatus

from flask import url_for

from tests.server.storage.views import check_annotate, check_tag_multiid


def test_versioninfo_list_route(cl_operator):
    """versioninfo list route test"""

    response = cl_operator.get(url_for('storage.versioninfo_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_versioninfo_list_json_route(cl_operator, versioninfo):
    """versioninfo list_json route test"""

    expected_product = versioninfo.product

    response = cl_operator.post(
        url_for('storage.versioninfo_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': expected_product}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['product'] == expected_product

    response = cl_operator.post(
        url_for(
            'storage.versioninfo_list_json_route',
            filter=f'Versioninfo.product=="{expected_product}"',
            product=expected_product,
            versionspec='>0'
        ),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['product'] == expected_product

    response = cl_operator.post(url_for('storage.versioninfo_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_versioninfo_list_json_route_query_form(cl_operator, service_factory, versioninfo_factory):
    """versioninfo list_json route test"""

    service1 = service_factory.create(port=1)
    versioninfo_factory.create(
        host_id=service1.host.id,
        host_address=service1.host.address,
        host_hostname=service1.host.hostname,
        service_proto=service1.proto,
        service_port=service1.port,
        product='apache httpd',
        version='1.0'
    )
    service2 = service_factory.create(port=2)
    versioninfo_factory.create(
        host_id=service2.host.id,
        host_address=service2.host.address,
        host_hostname=service2.host.hostname,
        service_proto=service2.proto,
        service_port=service2.port,
        product='apache httpd',
        version='1.1'
    )
    service3 = service_factory.create(port=3)
    versioninfo_factory.create(
        host_id=service3.host.id,
        host_address=service3.host.address,
        host_hostname=service3.host.hostname,
        service_proto=service3.proto,
        service_port=service3.port,
        product='apache httpd',
        version='1.2'
    )

    response = cl_operator.post(
        url_for(
            'storage.versioninfo_list_json_route',
            product='ApAcHe',
            versionspec=">=1.1"
        ),
        {'draw': 1, 'start': 1, 'length': 100}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert len(response_data['data']) == 1
    assert response_data['data'][0]['version'] == '1.2'


def test_versioninfo_tag_multiid_route(cl_operator, versioninfo):
    """versioninfo multi tag route for ajaxed toolbars test"""

    check_tag_multiid(cl_operator, 'storage.versioninfo_tag_multiid_route', versioninfo)


def test_versioninfo_annotate_route(cl_operator, versioninfo):
    """versioninfo annotate route test"""

    check_annotate(cl_operator, 'storage.versioninfo_annotate_route', versioninfo)
