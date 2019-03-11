"""controller note"""

from flask import current_app, redirect, render_template, request, url_for

from sner.server import db
from sner.server.controller.storage import blueprint
from sner.server.form import GenericButtonForm
from sner.server.form.storage import NoteForm
from sner.server.model.storage import Host, Note


@blueprint.route('/note/list')
def note_list_route():
	"""list notes"""

	page = request.args.get('page', 1, type=int)
	notes = Note.query.paginate(page, current_app.config['SNER_ITEMS_PER_PAGE'])
	return render_template('storage/note/list.html', notes=notes, generic_button_form=GenericButtonForm())


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

	host = Host.query.filter(Host.id == host_id).one_or_none()
	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_add_route', host_id=host_id), host=host)


@blueprint.route('/note/edit/<note_id>', methods=['GET', 'POST'])
def note_edit_route(note_id):
	"""edit note"""

	note = Note.query.get(note_id)
	form = NoteForm(obj=note)

	if form.validate_on_submit():
		form.populate_obj(note)
		db.session.commit()
		return redirect(url_for('storage.note_list_route'))

	host = note.host
	return render_template('storage/note/addedit.html', form=form, form_url=url_for('storage.note_edit_route', note_id=note_id), host=host)


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
