# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.excl tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.scheduler.models import Excl
from tests.server.scheduler.models import create_test_excl_network


def test_excl_list_route(cl_operator):
    """exclusion list route test"""

    response = cl_operator.get(url_for('scheduler.excl_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_excl_list_json_route(cl_operator, test_excl_network):
    """excl list_json route test"""

    response = cl_operator.post(
        url_for('scheduler.excl_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_excl_network.comment})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['comment'] == test_excl_network.comment

    response = cl_operator.post(
        url_for('scheduler.excl_list_json_route', filter='Excl.comment=="%s"' % test_excl_network.comment),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['comment'] == test_excl_network.comment


def test_excl_add_route(cl_operator):
    """exclusion add route test"""

    test_excl_network = create_test_excl_network()

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = test_excl_network.family
    form['value'] = test_excl_network.value
    form['comment'] = test_excl_network.comment
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    excl = Excl.query.filter(Excl.value == test_excl_network.value).one()
    assert excl.family == test_excl_network.family
    assert excl.value == test_excl_network.value

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'].force_value('invalid')
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//ul[@class="invalid-feedback"]/li[text()="Invalid family"]')

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = 'network'
    form['value'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "does not appear to be an IPv4 or IPv6 network")]')

    form = cl_operator.get(url_for('scheduler.excl_add_route')).form
    form['family'] = 'regex'
    form['value'] = '('
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid regex"]')


def test_excl_edit_route(cl_operator, test_excl_network):
    """exclusion edit route test"""

    form = cl_operator.get(url_for('scheduler.excl_edit_route', excl_id=test_excl_network.id)).form
    form['comment'] = form['comment'].value+' added comment'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    excl = Excl.query.filter(Excl.id == test_excl_network.id).one()
    assert 'added comment' in excl.comment


def test_excl_delete_route(cl_operator, test_excl_network):
    """excl delete route test"""

    form = cl_operator.get(url_for('scheduler.excl_delete_route', excl_id=test_excl_network.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Excl.query.filter(Excl.id == test_excl_network.id).one_or_none()


def test_excl_export_route(cl_operator, test_excl_network):
    """exclusion export route test"""

    response = cl_operator.get(url_for('scheduler.excl_export_route'))
    assert response.status_code == HTTPStatus.OK
    assert '"%s",' % test_excl_network.value in response.body.decode('utf-8')


def test_excl_import_route(cl_operator, test_excl_network):
    """exclusion import route test"""

    form = cl_operator.get(url_for('scheduler.excl_import_route')).form
    form['data'] = '"%s","%s","%s"\n' % (
        test_excl_network.family, test_excl_network.value, test_excl_network.comment)
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
