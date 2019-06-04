"""shared fixtures for selenium tests"""

import pytest

from tests.server.model.scheduler import test_job, test_queue, test_target, test_task  # noqa: F401  pylint: disable=unused-import
from tests.server.model.storage import test_host, test_note, test_service, test_vuln  # noqa: F401  pylint: disable=unused-import


@pytest.fixture
def firefox_options(firefox_options):  # pylint: disable=redefined-outer-name
    """override firefox options"""

    firefox_options.headless = True
    return firefox_options
