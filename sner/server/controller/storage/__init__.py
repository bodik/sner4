"""controller storage main module"""

from flask import Blueprint

from sner.server.model.storage import Host, Service


blueprint = Blueprint('storage', __name__)  # pylint: disable=invalid-name


def get_related_models(model_name, model_id):
    """get related host/service to bind vuln/note"""

    host, service = None, None
    if model_name == 'host':
        host = Host.query.get(model_id)
    elif model_name == 'service':
        service = Service.query.get(model_id)
        host = service.host
    return host, service


import sner.server.controller.storage.host  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.service  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.note  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.controller.storage.vuln  # noqa: E402,F401  pylint: disable=wrong-import-position
