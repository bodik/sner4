"""sner pytest config and fixtures"""

import pytest

from sner.server import db, create_app
from sner.server.command.db import db_remove


@pytest.fixture
def app():
    """yield application as pytest fixture"""

    _app = create_app(config_file='tests/sner.yaml')
    with _app.test_request_context():
        db_remove()
        db.create_all()
        yield _app
        db_remove()
