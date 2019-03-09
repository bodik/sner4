"""controller host"""

from flask import current_app, jsonify, redirect, render_template, request, url_for

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
from sner.server.model.storage import Host


@blueprint.route('/host/list')
def host_list_route():
	"""list hosts"""

	page = request.args.get('page', 1, type=int)
	hosts = Host.query.paginate(page, current_app.config['SNER_ITEMS_PER_PAGE'])
	return render_template('storage/host/list.html', hosts=hosts, generic_button_form=GenericButtonForm())


@blueprint.route('/host/delete/<host_id>', methods=['GET', 'POST'])
def host_delete_route(host_id):
	"""delete host"""

	host = Host.query.get(host_id)
	form = GenericButtonForm()
	if form.validate_on_submit():
		db.session.delete(host)
		db.session.commit()
		return redirect(url_for('storage.host_list_route'))
	return render_template('button_delete.html', form=form, form_url=url_for('storage.host_delete_route', host_id=host_id))
