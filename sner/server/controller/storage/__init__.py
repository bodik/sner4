"""controller storage main module"""

from flask import Blueprint, render_template
blueprint = Blueprint('storage', __name__) # pylint: disable=invalid-name


def render_host_address(host_id, host_address):
	"""ColumnDT rendering helper"""

	return render_template('storage/host/pagepart-address_link.html', host_id=host_id, host_address=host_address)


import sner.server.controller.storage.host # pylint: disable=wrong-import-position
import sner.server.controller.storage.service # pylint: disable=wrong-import-position
import sner.server.controller.storage.note # pylint: disable=wrong-import-position
import sner.server.controller.storage.vuln # pylint: disable=wrong-import-position
