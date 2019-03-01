"""pytest config and fixtures"""

import pytest
from webtest import TestApp
from sner.server import create_app

## import other fixtures to have them available in other tests
from tests.server.model.scheduler import test_job, test_queue, test_task # pylint: disable=unused-import


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
