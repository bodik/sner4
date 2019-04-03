"""controller storage main module"""

from flask import Blueprint, render_template
blueprint = Blueprint('storage', __name__) # pylint: disable=invalid-name


def render_columndt_host(data):
	return render_template(
		'storage/host/pagepart-view_link.html',
		host=dict(zip(['id', 'address', 'hostname'], data.split(' '))),
		show_hostname=True)


import sner.server.controller.storage.host # pylint: disable=wrong-import-position
import sner.server.controller.storage.service # pylint: disable=wrong-import-position
import sner.server.controller.storage.note # pylint: disable=wrong-import-position
import sner.server.controller.storage.vuln # pylint: disable=wrong-import-position
