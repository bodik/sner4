"""controller default tests"""

from flask import url_for
from http import HTTPStatus


def test_index(client):
	"""test root url"""

	response = client.get(url_for('index_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'logo.png' in response
