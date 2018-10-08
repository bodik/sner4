import pytest
from sner_web import create_app
from webtest import TestApp


@pytest.fixture
def client():
	"""A test client for the app."""
	app = create_app()
	ctx = app.test_request_context()
	ctx.push()
	yield TestApp(app)
	ctx.pop()
