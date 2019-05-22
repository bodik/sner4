"""sner tests package"""

from sner.server import db


def persist_and_detach(model):
    """would persist entity/model and detach. used for testing"""

    # TODO: is detaching necessary when database isolation betweeen tests is implemented ??
    db.session.add(model)
    db.session.commit()
    db.session.refresh(model)
    db.session.expunge(model)
    return model
