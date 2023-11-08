# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.views.vulnsearch tests
"""

import json
from http import HTTPStatus

from flask import url_for

from tests.server.storage.views import check_annotate, check_tag_multiid


def test_vulnsearch_list_route(cl_operator):
    """vulnsearch list route test"""

    response = cl_operator.get(url_for('storage.vulnsearch_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_vulnsearch_list_json_route(cl_operator, vulnsearch):
    """vulnsearch list_json route test"""

    response = cl_operator.post(
        url_for('storage.vulnsearch_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': vulnsearch.cveid}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['cveid'] == vulnsearch.cveid

    response = cl_operator.post(url_for('storage.vulnsearch_list_json_route', filter='invalid'), {'draw': 1, 'start': 0, 'length': 1}, status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_vulnsearch_tag_multiid_route(cl_operator, vulnsearch):
    """vulnsearch multi tag route for ajaxed toolbars test"""

    check_tag_multiid(cl_operator, 'storage.vulnsearch_tag_multiid_route', vulnsearch)


def test_vulnsearch_view_route(cl_operator, vulnsearch):
    """vulnsearch view route test"""

    response = cl_operator.get(url_for('storage.vulnsearch_view_route', vulnsearch_id=vulnsearch.id))
    assert response.status_code == HTTPStatus.OK


def test_vulnsearch_annotate_route(cl_operator, vulnsearch):
    """vulnsearch annotate route test"""

    check_annotate(cl_operator, 'storage.vulnsearch_annotate_route', vulnsearch)
