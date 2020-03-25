# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage note views
"""

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import func, literal_column
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.sqlafilter import filter_parser
from sner.server.storage.core import annotate_model, get_related_models
from sner.server.storage.forms import NoteForm
from sner.server.storage.models import Host, Note, Service
from sner.server.storage.views import blueprint
from sner.server.utils import relative_referrer, valid_next_url


@blueprint.route('/note/list')
@role_required('operator')
def note_list_route():
    """list notes"""

    return render_template('storage/note/list.html')


@blueprint.route('/note/list.json', methods=['GET', 'POST'])
@role_required('operator')
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
        ColumnDT(Note.tags, mData='tags'),
        ColumnDT(Note.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Note).outerjoin(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    notes = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(notes)


@blueprint.route('/note/add/<model_name>/<model_id>', methods=['GET', 'POST'])
@role_required('operator')
def note_add_route(model_name, model_id):
    """add note to host"""

    host, service = get_related_models(model_name, model_id)
    form = NoteForm(host_id=host.id, service_id=(service.id if service else None))

    if form.validate_on_submit():
        note = Note()
        form.populate_obj(note)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=note.host_id))

    return render_template('storage/note/addedit.html', form=form, host=host, service=service)


@blueprint.route('/note/edit/<note_id>', methods=['GET', 'POST'])
@role_required('operator')
def note_edit_route(note_id):
    """edit note"""

    note = Note.query.get(note_id)
    form = NoteForm(obj=note, return_url=relative_referrer())

    if form.validate_on_submit():
        form.populate_obj(note)
        db.session.commit()
        if valid_next_url(form.return_url.data):
            return redirect(form.return_url.data)

    return render_template('storage/note/addedit.html', form=form, host=note.host, service=note.service)


@blueprint.route('/note/delete/<note_id>', methods=['GET', 'POST'])
@role_required('operator')
def note_delete_route(note_id):
    """delete note"""

    form = ButtonForm()
    if form.validate_on_submit():
        note = Note.query.get(note_id)
        db.session.delete(note)
        db.session.commit()
        return redirect(url_for('storage.host_view_route', host_id=note.host_id))

    return render_template('button-delete.html', form=form)


@blueprint.route('/note/annotate/<model_id>', methods=['GET', 'POST'])
@role_required('operator')
def note_annotate_route(model_id):
    """annotate note"""
    return annotate_model(Note, model_id)


@blueprint.route('/note/view/<note_id>')
@role_required('operator')
def note_view_route(note_id):
    """view note"""

    note = Note.query.get(note_id)
    return render_template('storage/note/view.html', note=note, button_form=ButtonForm())
