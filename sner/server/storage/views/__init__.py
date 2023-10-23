# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage views
"""

from flask import Blueprint


blueprint = Blueprint('storage', __name__)  # pylint: disable=invalid-name

import sner.server.storage.views.host  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.quickjump  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.note  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.service  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.versioninfo  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.vulnsearch  # noqa: E402  pylint: disable=wrong-import-position
import sner.server.storage.views.vuln  # noqa: E402,F401  pylint: disable=wrong-import-position
