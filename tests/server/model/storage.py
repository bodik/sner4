"""storage test models"""

import pytest

from sner.server import db
from sner.server.model.storage import Host


def create_test_host():
	"""test host data"""

	return Host(
		address='127.128.129.130',
		hostname='localhost.localdomain')
