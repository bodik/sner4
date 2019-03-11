"""controller service"""

from flask import current_app, redirect, render_template, request, url_for

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
from sner.server.form.storage import ServiceForm
from sner.server.model.storage import Host, Service


@blueprint.route('/service/list')
def service_list_route():
	"""list services"""

	page = request.args.get('page', 1, type=int)
	services = Service.query.paginate(page, current_app.config['SNER_ITEMS_PER_PAGE'])
	return render_template('storage/service/list.html', services=services, generic_button_form=GenericButtonForm())


@blueprint.route('/service/add/<host_id>', methods=['GET', 'POST'])
def service_add_route(host_id):
	"""add service to host"""

	form = ServiceForm(host_id=host_id)

	if form.validate_on_submit():
		service = Service()
		form.populate_obj(service)
		db.session.add(service)
		db.session.commit()
		return redirect(url_for('storage.service_list_route'))

	host = Host.query.filter(Host.id == host_id).one_or_none()
	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_add_route', host_id=host_id), host=host)


@blueprint.route('/service/edit/<service_id>', methods=['GET', 'POST'])
def service_edit_route(service_id):
	"""edit service"""

	service = Service.query.get(service_id)
	form = ServiceForm(obj=service)

	if form.validate_on_submit():
		form.populate_obj(service)
		db.session.commit()
		return redirect(url_for('storage.service_list_route'))

	host = service.host
	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_edit_route', service_id=service_id), host=host)


@blueprint.route('/service/delete/<service_id>', methods=['GET', 'POST'])
def service_delete_route(service_id):
	"""delete service"""

	service = Service.query.get(service_id)
	form = GenericButtonForm()

	if form.validate_on_submit():
		db.session.delete(service)
		db.session.commit()
		return redirect(url_for('storage.service_list_route'))

	return render_template('button_delete.html', form=form, form_url=url_for('storage.service_delete_route', service_id=service_id))
