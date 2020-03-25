# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views tests
"""

from http import HTTPStatus

from flask import url_for


def test_index_route(cl_operator):
    """visuals index route test"""

    response = cl_operator.get(url_for('visuals.index_route'))
    assert response.status_code == HTTPStatus.OK
