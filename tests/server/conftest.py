"""pytest config and fixtures"""

import pytest
from webtest import TestApp

from sner.server import db, create_app
from sner.server.command.db import db_remove
## import all fixtures here; they will be available in all tests, import on module specific level would trigger redefined-outer-name
from tests.server.model.scheduler import test_job, test_queue, test_target, test_task # pylint: disable=unused-import
from tests.server.model.storage import test_host, test_note, test_service, test_vuln # pylint: disable=unused-import


@pytest.fixture
def app():
    """yield application as pytest fixture"""

    _app = create_app(config_file='tests/sner.yaml')
    with _app.test_request_context():
        db_remove()
        db.create_all()
        yield _app
        db_remove()


@pytest.fixture
def client(app): # pylint: disable=redefined-outer-name
    """create webtest testapp client"""
    return TestApp(app)


@pytest.fixture
def runner(app): # pylint: disable=redefined-outer-name
    """create cli test runner"""
    return app.test_cli_runner()
