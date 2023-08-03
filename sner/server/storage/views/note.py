# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage note views
"""

from http import HTTPStatus

import json
from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, Response, url_for
from sqlalchemy import func, literal_column

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.storage.core import annotate_model, get_related_models, model_delete_multiid, model_tag_multiid
from sner.server.storage.forms import MultiidForm, NoteForm, TagMultiidForm
from sner.server.storage.models import Host, Note, Service
from sner.server.storage.views import blueprint
from sner.server.utils import filter_query, relative_referrer, SnerJSONEncoder, valid_next_url


@blueprint.route('/note/list')
@session_required('operator')
def note_list_route():
    """list notes"""

    return render_template('storage/note/list.html')


@blueprint.route('/note/list.json', methods=['GET', 'POST'])
@session_required('operator')
def note_list_json_route():
    """list notes, data endpoint"""

    columns = [
        ColumnDT(Note.id, mData='id'),
        ColumnDT(Host.id, mData='host_id'),
        ColumnDT(Host.address, mData='host_address'),
        ColumnDT(Host.hostname, mData='host_hostname'),
        # break pylint duplicate-code
        ColumnDT(Service.proto, mData='service_proto'),
        ColumnDT(Service.port, mData='service_port'),
        ColumnDT(func.concat_ws('/', Service.port, Service.proto), mData='service'),
        ColumnDT(Note.via_target, mData='via_target'),
        ColumnDT(Note.xtype, mData='xtype'),
        ColumnDT(Note.data, mData='data'),
        ColumnDT(Note.tags, mData='tags'),
        ColumnDT(Note.comment, mData='comment'),
        ColumnDT(Note.created, mData='created'),
        ColumnDT(Note.modified, mData='modified'),
        ColumnDT(Note.import_time, mData='import_time'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Note).outerjoin(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    notes = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(notes, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/note/add/<model_name>/<model_id>', methods=['GET', 'POST'])
@session_required('operator')
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
@session_required('operator')
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
@session_required('operator')
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
@session_required('operator')
def note_annotate_route(model_id):
    """annotate note"""
    return annotate_model(Note, model_id)


@blueprint.route('/note/view/<note_id>')
@session_required('operator')
def note_view_route(note_id):
    """view note"""

    note = Note.query.get(note_id)
    return render_template('storage/note/view.html', note=note, button_form=ButtonForm())


@blueprint.route('/note/delete_multiid', methods=['POST'])
@session_required('operator')
def note_delete_multiid_route():
    """delete multiple note route"""

    form = MultiidForm()
    if form.validate_on_submit():
        model_delete_multiid(Note, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/note/tag_multiid', methods=['POST'])
@session_required('operator')
def note_tag_multiid_route():
    """tag multiple route"""

    form = TagMultiidForm()
    if form.validate_on_submit():
        model_tag_multiid(Note, form.action.data, form.tag.data, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST
