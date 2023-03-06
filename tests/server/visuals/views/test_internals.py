# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
visuals.views.internals tests
"""

from http import HTTPStatus

from flask import url_for


def test_internals_route(cl_admin):
    """internals route test"""

    response = cl_admin.get(url_for('visuals.internals_route'))
    assert response.status_code == HTTPStatus.OK
