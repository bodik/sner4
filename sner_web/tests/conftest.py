from sner_web.tests.test_profile import create_test_profile
import pytest
from sner_web import create_app, db
from webtest import TestApp


@pytest.fixture(scope="session")
def app(request):
	app = create_app()
	ctx = app.test_request_context()
	ctx.push()
	yield app
	ctx.pop()



@pytest.fixture(scope="session")
def client(app):
	"""A test client for the app."""
	return TestApp(app)
