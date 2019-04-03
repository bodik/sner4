"""controller vuln"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint, render_columndt_host
from sner.server.form import ButtonForm
from sner.server.form.storage import VulnForm
from sner.server.model.storage import Host, Service, Vuln


@blueprint.route('/vuln/list')
def vuln_list_route():
	"""list vulns"""

	return render_template('storage/vuln/list.html')


@blueprint.route('/vuln/list.json', methods=['GET', 'POST'])
def vuln_list_json_route():
	"""list vulns, data endpoint"""

	columns = [
		ColumnDT(Vuln.id, mData='id'),
		ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
		ColumnDT(Vuln.name, mData='name'),
		ColumnDT(Vuln.xtype, mData='xtype'),
		ColumnDT(Vuln.severity, mData='severity'),
		ColumnDT(Vuln.comment, mData='comment'),
		ColumnDT(Vuln.refs, mData='refs')
	]
	query = db.session.query().select_from(Vuln).outerjoin(Service, Vuln.service_id == Service.id)

	## endpoint is shared by generic service_list and host_view
	if 'host_id' in request.values:
		query = query.filter(Vuln.host_id == request.values.get('host_id'))
	else:
		query = query.join(Host, Vuln.host_id == Host.id)
		columns.insert(1, ColumnDT(func.concat(Host.id, ' ', Host.address, ' ', Host.hostname), mData='host'))

	vulns = DataTables(request.values.to_dict(), query, columns).output_result()
	if 'data' in vulns:
		button_form = ButtonForm()
		for vuln in vulns['data']:
			if 'host' in vuln:
				vuln['host'] = render_columndt_host(vuln['host'])
			vuln['severity'] = render_template('storage/vuln/pagepart-severity_label.html', severity=vuln['severity'])
			vuln['_buttons'] = render_template('storage/vuln/pagepart-controls.html', vuln=vuln, button_form=button_form)

	return jsonify(vulns)


@blueprint.route('/vuln/add/<model_name>/<model_id>', methods=['GET', 'POST'])
def vuln_add_route(model_name, model_id):
	"""add vuln to host or service"""

	(host, service) = (None, None)
	if model_name == 'host':
		host = Host.query.get(model_id)
	elif model_name == 'service':
		service = Service.query.get(model_id)
		host = service.host
	form = VulnForm(host_id=host.id, service_id=(service.id if service else None))

	if form.validate_on_submit():
		vuln = Vuln()
		form.populate_obj(vuln)
		db.session.add(vuln)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

	return render_template('storage/vuln/addedit.html', form=form, form_url=url_for('storage.vuln_add_route', model_name=model_name, model_id=model_id), host=host, service=service)


@blueprint.route('/vuln/edit/<vuln_id>', methods=['GET', 'POST'])
def vuln_edit_route(vuln_id):
	"""edit vuln"""

	vuln = Vuln.query.get(vuln_id)
	form = VulnForm(obj=vuln)

	if form.validate_on_submit():
		form.populate_obj(vuln)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

	return render_template('storage/vuln/addedit.html', form=form, form_url=url_for('storage.vuln_edit_route', vuln_id=vuln_id), host=vuln.host, service=vuln.service)


@blueprint.route('/vuln/delete/<vuln_id>', methods=['GET', 'POST'])
def vuln_delete_route(vuln_id):
	"""delete vuln"""

	vuln = Vuln.query.get(vuln_id)
	form = ButtonForm()
	if form.validate_on_submit():
		db.session.delete(vuln)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

	return render_template('button-delete.html', form=form, form_url=url_for('storage.vuln_delete_route', vuln_id=vuln_id))
