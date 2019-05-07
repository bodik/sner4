"""controller note"""

import json

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import ButtonForm
from sner.server.form.storage import NoteForm
from sner.server.model.storage import Host, Note, Service


@blueprint.app_template_filter()
def json_indent(data):
	"""parse and format json"""

	try:
		return json.dumps(json.loads(data), sort_keys=True, indent=4)
	except:
		return data


@blueprint.route('/note/list')
def note_list_route():
	"""list notes"""

	return render_template('storage/note/list.html')


@blueprint.route('/note/list.json', methods=['GET', 'POST'])
def note_list_json_route():
	"""list notes, data endpoint"""

	columns = [
		ColumnDT(Note.id, mData='id'),
		ColumnDT(Host.id, mData='host_id'),
		ColumnDT(Host.address, mData='host_address'),
		ColumnDT(Host.hostname, mData='host_hostname'),
		ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
		ColumnDT(Note.xtype, mData='xtype'),
		ColumnDT(Note.data, mData='data'),
		ColumnDT(Note.comment, mData='comment'),
		ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
	]
	query = db.session.query().select_from(Note).join(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id)

	## filtering
	if 'host_id' in request.values:
		query = query.filter(Note.host_id == request.values.get('host_id'))

	notes = DataTables(request.values.to_dict(), query, columns).output_result()
	return jsonify(notes)


@blueprint.route('/note/add/<model_name>/<model_id>', methods=['GET', 'POST'])
def note_add_route(model_name, model_id):
	"""add note to host"""

	(host, service) = (None, None)
	if model_name == 'host':
		host = Host.query.get(model_id)
	elif model_name == 'service':
		service = Service.query.get(model_id)
		host = service.host
	form = NoteForm(host_id=host.id, service_id=(service.id if service else None))

	if form.validate_on_submit():
		note = Note()
		form.populate_obj(note)
		db.session.add(note)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=note.host_id))

	return render_template(
		'storage/note/addedit.html',
		form=form,
		form_url=url_for('storage.note_add_route', model_name=model_name, model_id=model_id),
		host=host,
		service=service)


@blueprint.route('/note/edit/<note_id>', methods=['GET', 'POST'])
def note_edit_route(note_id):
	"""edit note"""

	note = Note.query.get(note_id)
	form = NoteForm(obj=note)

	if form.validate_on_submit():
		form.populate_obj(note)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=note.host_id))

	return render_template(
		'storage/note/addedit.html',
		form=form,
		form_url=url_for('storage.note_edit_route', note_id=note_id),
		host=note.host,
		service=note.service)


@blueprint.route('/note/delete/<note_id>', methods=['GET', 'POST'])
def note_delete_route(note_id):
	"""delete note"""

	note = Note.query.get(note_id)
	form = ButtonForm()
	if form.validate_on_submit():
		db.session.delete(note)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=note.host_id))

	return render_template('button-delete.html', form=form, form_url=url_for('storage.note_delete_route', note_id=note_id))


@blueprint.route('/note/view/<note_id>')
def note_view_route(note_id):
	"""view note"""

	note = Note.query.get(note_id)
	return render_template('storage/note/view.html', note=note, button_form=ButtonForm())
