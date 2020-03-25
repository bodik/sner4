# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.vuln tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.storage.models import Vuln
from tests.server import get_csrf_token
from tests.server.storage.models import create_test_vuln
from tests.server.storage.views import check_annotate, check_tag_multiid


def test_vuln_list_route(cl_operator):
    """vuln list route test"""

    response = cl_operator.get(url_for('storage.vuln_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_vuln_list_json_route(cl_operator, test_vuln):
    """vuln list_json route test"""

    response = cl_operator.post(url_for('storage.vuln_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_vuln.name})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_vuln.name in response_data['data'][0]['name']

    response = cl_operator.post(
        url_for('storage.vuln_list_json_route', filter='Vuln.name=="%s"' % test_vuln.name),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_vuln.name in response_data['data'][0]['name']


def test_vuln_add_route(cl_operator, test_host, test_service):
    """vuln add route test"""

    test_vuln = create_test_vuln(test_host, test_service)

    form = cl_operator.get(url_for('storage.vuln_add_route', model_name='service', model_id=test_vuln.service.id)).form
    form['name'] = test_vuln.name
    form['xtype'] = test_vuln.xtype
    form['severity'] = str(test_vuln.severity)
    form['descr'] = test_vuln.descr
    form['data'] = test_vuln.descr
    form['refs'] = '\n'.join(test_vuln.refs)
    form['tags'] = '\n'.join(test_vuln.tags)
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    vuln = Vuln.query.filter(Vuln.name == test_vuln.name).one()
    assert vuln.xtype == test_vuln.xtype
    assert vuln.severity == test_vuln.severity
    assert vuln.refs == test_vuln.refs
    assert vuln.tags == test_vuln.tags


def test_vuln_edit_route(cl_operator, test_vuln):
    """vuln edit route test"""

    form = cl_operator.get(url_for('storage.vuln_edit_route', vuln_id=test_vuln.id)).form
    form['name'] = 'edited '+form['name'].value
    form['tags'] = form['tags'].value + '\nedited'
    form['return_url'] = url_for('storage.vuln_list_route')
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    vuln = Vuln.query.get(test_vuln.id)
    assert vuln.name == form['name'].value
    assert len(vuln.tags) == 3


def test_vuln_delete_route(cl_operator, test_vuln):
    """vuln delete route test"""

    form = cl_operator.get(url_for('storage.vuln_delete_route', vuln_id=test_vuln.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Vuln.query.get(test_vuln.id)


def test_vuln_annotate_route(cl_operator, test_vuln):
    """vuln annotate route test"""

    check_annotate(cl_operator, 'storage.vuln_annotate_route', test_vuln)


def test_vuln_view_route(cl_operator, test_vuln):
    """vuln view route test"""

    response = cl_operator.get(url_for('storage.vuln_view_route', vuln_id=test_vuln.id))
    assert response.status_code == HTTPStatus.OK

    assert '<pre>%s</pre>' % test_vuln.data in response


def test_vuln_delete_multiid_route(cl_operator, test_vuln):
    """vuln multi delete route for ajaxed toolbars test"""

    data = {'ids-0': test_vuln.id, 'csrf_token': get_csrf_token(cl_operator)}
    response = cl_operator.post(url_for('storage.vuln_delete_multiid_route'), data)
    assert response.status_code == HTTPStatus.OK
    assert not Vuln.query.get(test_vuln.id)

    response = cl_operator.post(url_for('storage.vuln_delete_multiid_route'), {}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_vuln_tag_multiid_route(cl_operator, test_vuln):
    """vuln multi tag route for ajaxed toolbars test"""

    check_tag_multiid(cl_operator, 'storage.vuln_tag_multiid_route', test_vuln)


def test_vuln_grouped_route(cl_operator):
    """vuln grouped route test"""

    response = cl_operator.get(url_for('storage.vuln_grouped_route'))
    assert response.status_code == HTTPStatus.OK


def test_vuln_grouped_json_route(cl_operator, test_vuln):
    """vuln grouped json route test"""

    response = cl_operator.post(url_for('storage.vuln_grouped_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_vuln.name})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_vuln.name in response_data['data'][0]['name']

    response = cl_operator.post(
        url_for('storage.vuln_grouped_json_route', filter='Vuln.name=="%s"' % test_vuln.name),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert test_vuln.name in response_data['data'][0]['name']


def test_vuln_report_route(cl_operator, test_vuln):
    """vuln report route test"""

    response = cl_operator.get(url_for('storage.vuln_report_route'))
    assert response.status_code == HTTPStatus.OK
    assert ',"%s",' % test_vuln.name in response.body.decode('utf-8')
