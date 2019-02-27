"""pytest config and fixtures"""

import pytest
from webtest import TestApp
from sner.server import create_app


@pytest.fixture(scope='session')
def app():
	"""yield application as pytest fixture"""

	_app = create_app()
	ctx = _app.test_request_context()
	ctx.push()
	yield _app
	ctx.pop()


@pytest.fixture(scope='session')
def client(app): # pylint: disable=redefined-outer-name
	"""create webtest testapp client"""
	return TestApp(app)


@pytest.fixture(scope='session')
def runner(app): # pylint: disable=redefined-outer-name
	"""create cli test runner"""
	return app.test_cli_runner()
