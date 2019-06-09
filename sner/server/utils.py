"""misc utils used in server"""

import json

from sner.server.model.scheduler import ExclFamily


class SnerJSONEncoder(json.JSONEncoder):
    """Custom encoder to handle serializations of various types used within the project"""

    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, ExclFamily):
            return str(o)

        return super().default(o)  # pragma: no cover  ; no such elements
