"""tests subpackage"""

from sner.server.extensions import db


def persist_and_detach(model):
	"""would persist entity/model and detach. used mainly for testing"""

	db.session.add(model)
	db.session.commit()
	db.session.refresh(model)
	db.session.expunge(model)
	return model
