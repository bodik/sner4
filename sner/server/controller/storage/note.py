"""controller note"""

from datatables import ColumnDT, DataTables
from flask import current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy.sql import func

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
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
		ColumnDT(Note.id, None, "id"),
		ColumnDT(func.concat(Host.address, ' (', Host.hostname, ')'), None, "host"),
		ColumnDT(Note.ntype, None, "ntype"),
		ColumnDT(Note.data, None, "data"),
		ColumnDT(Note.created, None, "created"),
		ColumnDT(Note.modified, None, "modified")
	]
	notes = DataTables(request.values.to_dict(), db.session.query().select_from(Note).join(Host), columns).output_result()

	if "data" in notes:
		generic_button_form = GenericButtonForm()
		for note in notes["data"]:
			note["created"] = note["created"].strftime('%Y-%m-%dT%H:%M:%S')
			note["modified"] = note["modified"].strftime('%Y-%m-%dT%H:%M:%S')
			note["_buttons"] = render_template('storage/note/list_datatable_controls.html', note=note, generic_button_form=generic_button_form)

	return jsonify(notes)


@blueprint.route('/note/add/<host_id>', methods=['GET', 'POST'])
def note_add_route(host_id):
	"""add note to host"""

	form = NoteForm(host_id=host_id)

	if form.validate_on_submit():
		note = Note()
		form.populate_obj(note)
		db.session.add(note)
		db.session.commit()
		return redirect(url_for('storage.note_list_route'))

	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_add_route', host_id=host_id))


@blueprint.route('/note/edit/<note_id>', methods=['GET', 'POST'])
def note_edit_route(note_id):
	"""edit note"""

	note = Note.query.get(note_id)
	form = NoteForm(obj=note)

	if form.validate_on_submit():
		form.populate_obj(note)
		db.session.commit()
		return redirect(url_for('storage.note_list_route'))

	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_edit_route', note_id=note_id))


@blueprint.route('/note/delete/<note_id>', methods=['GET', 'POST'])
def note_delete_route(note_id):
	"""delete note"""

	note = Note.query.get(note_id)
	form = GenericButtonForm()
	if form.validate_on_submit():
		db.session.delete(note)
		db.session.commit()
		return redirect(url_for('storage.note_list_route'))
	return render_template('button_delete.html', form=form, form_url=url_for('storage.note_delete_route', note_id=note_id))
