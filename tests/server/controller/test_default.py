"""controller default tests"""

from http import HTTPStatus

from flask import url_for


def test_index_route(client):
    """test root url"""

    response = client.get(url_for('index_route'))
    assert response.status_code == HTTPStatus.OK
    assert 'logo.png' in response
