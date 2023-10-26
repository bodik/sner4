# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.core tests
"""

from http import HTTPStatus

from flask import url_for


def test_auth_session(cl_user):
    """test session auth"""

    response = cl_user.get(url_for('auth.profile_route'))
    assert response.status_code == HTTPStatus.OK

    # session authenticated user should not access api
    response = cl_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': '192.0.2.1'}, status='*')
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_auth_apikey(api_user):
    """test session auth"""

    # apikey authenticated user should not access webui
    response = api_user.get(url_for('auth.profile_route'), status='*')
    assert response.status_code == HTTPStatus.FORBIDDEN

    response = api_user.post_json(url_for('api.v2_public_storage_host_route'), {'address': '192.0.2.1'})
    assert response.status_code == HTTPStatus.OK
