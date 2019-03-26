"""controller note"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import ButtonForm
from sner.server.form.storage import NoteForm
from sner.server.model.storage import Host, Note


@blueprint.route('/note/list')
def note_list_route():
	"""list notes"""

	return render_template('storage/note/list.html')


@blueprint.route('/note/list.json', methods=['GET', 'POST'])
def note_list_json_route():
	"""list notes, data endpoint"""

	columns = [
		ColumnDT(Note.id, mData='id'),
		ColumnDT(Note.ntype, mData='ntype'),
		ColumnDT(Note.data, mData='data'),
		ColumnDT(Note.comment, mData='comment')
	]
	query = db.session.query().select_from(Note)

	## endpoint is shared by generic service_list and host_view
	if 'host_id' in request.values:
		query = query.filter(Note.host_id == request.values.get('host_id'))
	else:
		query = query.join(Host)
		columns.insert(1, ColumnDT(func.concat(Host.id, ' ', Host.address, ' ', Host.hostname), mData='host'))

	notes = DataTables(request.values.to_dict(), query, columns).output_result()
	if 'data' in notes:
		button_form = ButtonForm()
		for note in notes['data']:
			note['_buttons'] = render_template('storage/note/pagepart-controls.html', note=note, button_form=button_form)

	return jsonify(notes)


@blueprint.route('/note/add/<host_id>', methods=['GET', 'POST'])
def note_add_route(host_id):
	"""add note to host"""

	host = Host.query.get(host_id)
	form = NoteForm(host_id=host_id)

	if form.validate_on_submit():
		note = Note()
		form.populate_obj(note)
		db.session.add(note)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=note.host_id))

	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_add_route', host_id=host_id), host=host)


@blueprint.route('/note/edit/<note_id>', methods=['GET', 'POST'])
def note_edit_route(note_id):
	"""edit note"""

	note = Note.query.get(note_id)
	form = NoteForm(obj=note)

	if form.validate_on_submit():
		form.populate_obj(note)
		db.session.commit()
		return redirect(url_for('storage.host_view_route', host_id=note.host_id))

	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_edit_route', note_id=note_id), host=note.host)


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
