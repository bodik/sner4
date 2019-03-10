"""storage test models"""

import pytest

from sner.server import db
from sner.server.model.storage import Host
from tests.server import persist_and_detach


def create_test_host():
	"""test host data"""

	return Host(
		address='127.128.129.130',
		hostname='localhost.localdomain',
		os='some linux')

@pytest.fixture()
def test_host():
	"""persistent test host"""

	tmp_host = persist_and_detach(create_test_host())
	tmp_id = tmp_host.id
	yield tmp_host
	db.session.delete(Host.query.get(tmp_id))
	db.session.commit()
