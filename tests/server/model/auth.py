"""auth tests models"""

from uuid import uuid4

import pytest

from sner.server.model.auth import User
from tests import persist_and_detach


def create_test_user():
    """test user data"""

    return User(
        username='user1',
        password=str(uuid4()),
        active=True,
        roles=['user'])


@pytest.fixture
def test_user():
    """persistent test task"""

    yield persist_and_detach(create_test_user())
