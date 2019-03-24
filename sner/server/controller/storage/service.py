"""controller service"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
from sner.server.form.storage import ServiceForm
from sner.server.model.storage import Host, Service


@blueprint.route('/service/list')
def service_list_route():
	"""list services"""

	return render_template('storage/service/list.html')


@blueprint.route('/service/list.json', methods=['GET', 'POST'])
def service_list_json_route():
	"""list services, data endpoint"""

	columns = [
		ColumnDT(Service.id, None, "id"),
		ColumnDT(Service.proto, None, "proto"),
		ColumnDT(Service.port, None, "port"),
		ColumnDT(Service.name, None, "name"),
		ColumnDT(Service.state, None, "state"),
		ColumnDT(Service.info, None, "info"),
		ColumnDT(Service.created, None, "created"),
		ColumnDT(Service.modified, None, "modified")
	]
	query = db.session.query().select_from(Service)
	if 'host_id' in request.values:
		query = query.filter(Service.host_id == request.values.get('host_id'))
	else:
		query = query.join(Host)
		columns.insert(1, ColumnDT(func.concat(Host.address, ' (', Host.hostname, ')'), None, "host"))

	services = DataTables(request.values.to_dict(), query, columns).output_result()
	if "data" in services:
		generic_button_form = GenericButtonForm()
		for service in services["data"]:
			service["created"] = service["created"].strftime('%Y-%m-%dT%H:%M:%S')
			service["modified"] = service["modified"].strftime('%Y-%m-%dT%H:%M:%S')
			service["_buttons"] = render_template('storage/service/list_datatable_controls.html', service=service, generic_button_form=generic_button_form)

	return jsonify(services)


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

	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_add_route', host_id=host_id))


@blueprint.route('/service/edit/<service_id>', methods=['GET', 'POST'])
def service_edit_route(service_id):
	"""edit service"""

	service = Service.query.get(service_id)
	form = ServiceForm(obj=service)

	if form.validate_on_submit():
		form.populate_obj(service)
		db.session.commit()
		return redirect(url_for('storage.service_list_route'))

	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_edit_route', service_id=service_id))


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
