"""pytest config and fixtures"""

import pytest
from webtest import TestApp

# import all fixtures here; they will be available in all tests, import on module specific level would trigger redefined-outer-name
from tests.server.model.scheduler import test_excl_network, test_job, test_job_completed, test_queue, test_target, test_task  # noqa: F401,E501  pylint: disable=unused-import
from tests.server.model.storage import test_host, test_note, test_service, test_vuln  # noqa: F401  pylint: disable=unused-import


@pytest.fixture
def client(app):  # pylint: disable=redefined-outer-name
    """create webtest testapp client"""
    return TestApp(app)


@pytest.fixture
def runner(app):  # pylint: disable=redefined-outer-name
    """create cli test runner"""
    return app.test_cli_runner()
