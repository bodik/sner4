"""shared utilities"""

from sner_web.extensions import db


def wait_for_lock(table):
	while True:
		try:
			db.session.execute('LOCK TABLE %s' % table)
			break
		except Exception:
			db.session.rollback()
			time.sleep(0.01)
