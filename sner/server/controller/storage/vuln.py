"""controller vuln"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint, render_host_address
from sner.server.form import ButtonForm
from sner.server.form.storage import VulnForm
from sner.server.model.storage import Host, Service, Vuln


@blueprint.app_template_filter()
def url_for_ref(ref):
	"""generate anchor url for vuln.ref"""

	try:
		rtype, rval = ref.split('-', maxsplit=1)
	except ValueError:
		return '#'

	url = '#'
	if rtype == 'URL':
		url = rval
	elif rtype == 'CVE':
		url = 'https://cvedetails.com/cve/CVE-%s' % rval
	elif rtype == 'NSS':
		url = 'https://www.tenable.com/plugins/nessus/%s' % rval
	elif rtype == 'BID':
		url = 'http://www.securityfocus.com/bid/%s' % rval
	elif rtype == 'CERT':
		url = 'https://www.kb.cert.org/vuls/id/%s' % rval
	elif rtype == 'EDB':
		url = 'https://www.exploit-db.com/exploits/%s' % rval.replace('ID-', '')
	elif rtype == 'SN':
		url = url_for('storage.note_view_route', note_id=rval)

	return url


@blueprint.app_template_filter()
def text_for_ref(ref):
	"""generate anchor text for vuln.ref"""

	try:
		rtype, _ = ref.split('-', maxsplit=1)
	except ValueError:
		return ref

	return 'URL' if rtype == 'URL' else ref


@blueprint.route('/vuln/list')
def vuln_list_route():
	"""list vulns"""

	return render_template('storage/vuln/list.html')


@blueprint.route('/vuln/list.json', methods=['GET', 'POST'])
def vuln_list_json_route():
	"""list vulns, data endpoint"""

	columns = [
		ColumnDT(Vuln.id, mData='id'),
		ColumnDT(func.concat(Host.id, ' ', Host.address), mData='address'),
		ColumnDT(Host.hostname, mData='hostname'),
		ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
		ColumnDT(Vuln.name, mData='name'),
		ColumnDT(Vuln.xtype, mData='xtype'),
		ColumnDT(Vuln.severity, mData='severity'),
		ColumnDT(Vuln.refs, mData='refs'),
		ColumnDT(Vuln.comment, mData='comment')
	]
	query = db.session.query().select_from(Vuln).join(Host, Vuln.host_id == Host.id).outerjoin(Service, Vuln.service_id == Service.id)

	## filtering
	if 'host_id' in request.values:
		query = query.filter(Vuln.host_id == request.values.get('host_id'))

	vulns = DataTables(request.values.to_dict(), query, columns).output_result()
	if 'data' in vulns:
		button_form = ButtonForm()
		for vuln in vulns['data']:
			vuln['address'] = render_host_address(*vuln['address'].split(' '))
			vuln['name'] = render_template('storage/vuln/pagepart-name_link.html', vuln=vuln)
			vuln['severity'] = render_template('storage/vuln/pagepart-severity_label.html', vuln=vuln)
			vuln['refs'] = render_template('storage/vuln/pagepart-refs.html', vuln=vuln)
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

	return render_template(
		'storage/vuln/addedit.html',
		form=form,
		form_url=url_for('storage.vuln_add_route', model_name=model_name, model_id=model_id),
		host=host,
		service=service)


@blueprint.route('/vuln/edit/<vuln_id>', methods=['GET', 'POST'])
def vuln_edit_route(vuln_id):
	"""edit vuln"""

	vuln = Vuln.query.get(vuln_id)
	form = VulnForm(obj=vuln)

	if form.validate_on_submit():
		form.populate_obj(vuln)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=vuln.host_id))

	return render_template(
		'storage/vuln/addedit.html',
		form=form,
		form_url=url_for('storage.vuln_edit_route', vuln_id=vuln_id),
		host=vuln.host,
		service=vuln.service)


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


@blueprint.route('/vuln/view/<vuln_id>')
def vuln_view_route(vuln_id):
	"""view vuln"""

	vuln = Vuln.query.get(vuln_id)
	return render_template('storage/vuln/view.html', vuln=vuln, button_form=ButtonForm())
