"""
shared utilities
"""

import time
from sner.server.extensions import db


def wait_for_lock(table):
	"""
	wait for database lock
	"""

	#TODO: passive wait for lock
	while True:
		try:
			db.session.execute('LOCK TABLE %s' % table)
			break
		except Exception:
			db.session.rollback()
			time.sleep(0.01)
