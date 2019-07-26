# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
internal flask_jsglue implementation test/coverage
"""

from http import HTTPStatus

from flask import url_for


def test_jsglue(client):
    """test jsglue generator"""

    response = client.get(url_for('serve_js'))
    assert response.status_code == HTTPStatus.OK
