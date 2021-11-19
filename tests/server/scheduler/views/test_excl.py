# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.excl tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.scheduler.models import Excl


def test_excl_list_route(cl_operator):
    """exclusion list route test"""

    response = cl_operator.get(url_for('scheduler.excl_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_excl_list_json_route(cl_operator, excl_network):
    """excl list_json route test"""

    response = cl_operator.post(
        url_for('scheduler.excl_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': excl_network.comment})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['comment'] == excl_network.comment

    response = cl_operator.post(
        url_for('scheduler.excl_list_json_route', filter=f'Excl.comment=="{excl_network.comment}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['comment'] == excl_network.comment


def test_excl_add_route(cl_operator, excl_network_factory):
    """exclusion add route test"""

    aexcl_network = excl_network_factory.build()

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = aexcl_network.family
    form['value'] = aexcl_network.value
    form['comment'] = aexcl_network.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    texcl = Excl.query.filter(Excl.value == aexcl_network.value).one()
    assert texcl.family == aexcl_network.family
    assert texcl.value == aexcl_network.value

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'].force_value('invalid')
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//ul[@class="invalid-feedback"]/li[text()="Invalid family"]')

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = 'NETWORK'
    form['value'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "does not appear to be an IPv4 or IPv6 network")]')

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = 'REGEX'
    form['value'] = '('
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid regex"]')


def test_excl_edit_route(cl_operator, excl_network):
    """exclusion edit route test"""

    form = cl_operator.get(url_for('scheduler.excl_edit_route', excl_id=excl_network.id)).form
    form['comment'] = form['comment'].value + ' added comment'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    texcl = Excl.query.filter(Excl.id == excl_network.id).one()
    assert 'added comment' in texcl.comment


def test_excl_delete_route(cl_operator, excl_network):
    """excl delete route test"""

    form = cl_operator.get(url_for('scheduler.excl_delete_route', excl_id=excl_network.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Excl.query.filter(Excl.id == excl_network.id).one_or_none()


def test_excl_export_route(cl_operator, excl_network):
    """exclusion export route test"""

    response = cl_operator.get(url_for('scheduler.excl_export_route'))
    assert response.status_code == HTTPStatus.OK
    assert f'"{excl_network.value}",' in response.body.decode('utf-8')


def test_excl_import_route(cl_operator, excl_network):
    """exclusion import route test"""

    form = cl_operator.get(url_for('scheduler.excl_import_route')).form
    form['data'] = f'"{excl_network.family}","{excl_network.value}","{excl_network.comment}"\n'
    form['replace'] = 1
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert len(Excl.query.all()) == 1

    form = cl_operator.get(url_for('scheduler.excl_import_route')).form
    form['data'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Import failed\');")]')
    assert len(Excl.query.all()) == 1
