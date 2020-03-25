# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler excl views
"""

import csv
import json
from datetime import datetime
from io import StringIO

import psycopg2
from datatables import ColumnDT, DataTables
from flask import current_app, flash, redirect, render_template, request, Response, url_for
from sqlalchemy import literal_column
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.scheduler.forms import ExclForm, ExclImportForm
from sner.server.scheduler.models import Excl, ExclFamily
from sner.server.scheduler.views import blueprint
from sner.server.sqlafilter import filter_parser
from sner.server.utils import SnerJSONEncoder


EXPORT_FIELDNAMES = ['family', 'value', 'comment']


@blueprint.route('/excl/list')
@role_required('operator')
def excl_list_route():
    """list target exclustions"""

    return render_template('scheduler/excl/list.html')


@blueprint.route('/excl/list.json', methods=['GET', 'POST'])
@role_required('operator')
def excl_list_json_route():
    """list target exclusions, data endpoint"""

    columns = [
        ColumnDT(Excl.id, mData='id'),
        ColumnDT(Excl.family, mData='family'),
        ColumnDT(Excl.value, mData='value'),
        ColumnDT(Excl.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Excl)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    excls = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(excls, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/excl/add', methods=['GET', 'POST'])
@role_required('operator')
def excl_add_route():
    """add exclustion"""

    form = ExclForm()

    if form.validate_on_submit():
        excl = Excl()
        form.populate_obj(excl)
        db.session.add(excl)
        db.session.commit()
        return redirect(url_for('scheduler.excl_list_route'))

    return render_template('scheduler/excl/addedit.html', form=form)


@blueprint.route('/excl/edit/<excl_id>', methods=['GET', 'POST'])
@role_required('operator')
def excl_edit_route(excl_id):
    """edit exclustion"""

    excl = Excl.query.get(excl_id)
    form = ExclForm(obj=excl)

    if form.validate_on_submit():
        form.populate_obj(excl)
        db.session.commit()
        return redirect(url_for('scheduler.excl_list_route'))

    return render_template('scheduler/excl/addedit.html', form=form)


@blueprint.route('/excl/delete/<excl_id>', methods=['GET', 'POST'])
@role_required('operator')
def excl_delete_route(excl_id):
    """delete exclusion"""

    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(Excl.query.get(excl_id))
        db.session.commit()
        return redirect(url_for('scheduler.excl_list_route'))

    return render_template('button-delete.html', form=form)


@blueprint.route('/excl/import', methods=['GET', 'POST'])
@role_required('operator')
def excl_import_route():
    """import exclustions from csv"""

    form = ExclImportForm()
    if form.validate_on_submit():
        imported = []
        try:
            for row in csv.DictReader(StringIO(form.data.data), EXPORT_FIELDNAMES, quoting=csv.QUOTE_MINIMAL):
                imported.append(Excl(family=ExclFamily(row['family']), value=row['value'], comment=row['comment']))

            if imported:
                if form.replace.data:
                    db.session.query(Excl).delete()
                for tmp in imported:
                    db.session.add(tmp)
                db.session.commit()
                return redirect(url_for('scheduler.excl_list_route'))
        except (csv.Error, ValueError, SQLAlchemyError, psycopg2.Error) as e:
            db.session.rollback()
            current_app.logger.exception(e)
            flash('Import failed', 'error')

    return render_template('scheduler/excl/import.html', form=form)


@blueprint.route('/excl/export')
@role_required('operator')
def excl_export_route():
    """export excls to csv"""

    output_buffer = StringIO()
    output = csv.DictWriter(output_buffer, EXPORT_FIELDNAMES, restval='', quoting=csv.QUOTE_ALL)
    for row in db.session.query(Excl.family, Excl.value, Excl.comment).all():
        output.writerow(row._asdict())

    return Response(
        output_buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=excl-%s.csv' % datetime.now().isoformat()})
