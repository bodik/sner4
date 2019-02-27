from flask import url_for
from http import HTTPStatus


def test_index(client):
	response = client.get(url_for("index"))
	assert response.status_code == HTTPStatus.OK
	assert b"logo.png" in response
