"""controller service"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import distinct, func

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import ButtonForm
from sner.server.form.storage import ServiceForm
from sner.server.model.storage import Host, Service


VIZPORTS_LOW = 10.0
VIZPORTS_HIGH = 100.0


@blueprint.route('/service/list')
def service_list_route():
	"""list services"""

	return render_template('storage/service/list.html')


@blueprint.route('/service/list.json', methods=['GET', 'POST'])
def service_list_json_route():
	"""list services, data endpoint"""

	columns = [
		ColumnDT(Service.id, mData='id'),
		ColumnDT(Service.proto, mData='proto'),
		ColumnDT(Service.port, mData='port'),
		ColumnDT(Service.name, mData='name'),
		ColumnDT(Service.state, mData='state'),
		ColumnDT(Service.info, mData='info')
	]
	query = db.session.query().select_from(Service)

	## endpoint is shared by generic service_list and host_view
	if 'host_id' in request.values:
		query = query.filter(Service.host_id == request.values.get('host_id'))
	else:
		query = query.join(Host)
		columns.insert(1, ColumnDT(func.concat(Host.id, ' ', Host.address, ' ', Host.hostname), mData='host'))

	## port filtering is used from service_vizports
	if 'port' in request.values:
		query = query.filter(Service.port == request.values.get('port'))

	services = DataTables(request.values.to_dict(), query, columns).output_result()
	if 'data' in services:
		button_form = ButtonForm()
		for service in services['data']:
			service['_buttons'] = render_template('storage/service/pagepart-controls.html', service=service, button_form=button_form)

	return jsonify(services)


@blueprint.route('/service/add/<host_id>', methods=['GET', 'POST'])
def service_add_route(host_id):
	"""add service to host"""

	host = Host.query.get(host_id)
	form = ServiceForm(host_id=host_id)

	if form.validate_on_submit():
		service = Service()
		form.populate_obj(service)
		db.session.add(service)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=service.host_id))

	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_add_route', host_id=host_id), host=host)


@blueprint.route('/service/edit/<service_id>', methods=['GET', 'POST'])
def service_edit_route(service_id):
	"""edit service"""

	service = Service.query.get(service_id)
	form = ServiceForm(obj=service)

	if form.validate_on_submit():
		form.populate_obj(service)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=service.host_id))

	return render_template('storage/service/addedit.html', form=form, form_url=url_for('storage.service_edit_route', service_id=service_id), host=service.host)


@blueprint.route('/service/delete/<service_id>', methods=['GET', 'POST'])
def service_delete_route(service_id):
	"""delete service"""

	service = Service.query.get(service_id)
	form = ButtonForm()

	if form.validate_on_submit():
		db.session.delete(service)
		db.session.commit()
		return redirect(url_for('storage.service_list_route'))

	return render_template('button-delete.html', form=form, form_url=url_for('storage.service_delete_route', service_id=service_id))


@blueprint.route('/service/vizports')
def service_vizports_route():
	"""visualize portmap"""

	data = []
	for port, count in db.session.query(Service.port, func.count(Service.id)).order_by(Service.port).group_by(Service.port).all():
		data.append({'port': port, 'count': count})

	## compute sizing for rendered element
	lowest = min(data, key=lambda x: x['count'])['count']
	highest = max(data, key=lambda x: x['count'])['count']
	coef = (VIZPORTS_HIGH-VIZPORTS_LOW) / max(1, (highest-lowest))
	for tmp in data:
		tmp['size'] = VIZPORTS_LOW + ((tmp['count']-lowest)*coef)

	return render_template('storage/service/vizports.html', data=data)


@blueprint.route('/service/portstat/<port>')
def service_portstat_route(port):
	"""generate port statistics fragment"""

	stats = {}
	query = db.session.query(Service.proto, func.count(Service.id)).filter(Service.port == port).order_by(Service.proto).group_by(Service.proto)
	for proto, count in query.all():
		stats[proto] = count
	banners = db.session.query(distinct(Service.info)).filter(Service.port == port, Service.info != '').all()
	hosts = db.session \
			.query(func.concat(Host.address, ' (', Host.hostname, ')'), Host.id) \
			.select_from(Service).join(Host) \
			.filter(Service.port == port).all()

	return render_template('storage/service/portstat.html', port=port, stats=stats, banners=banners, hosts=hosts)
