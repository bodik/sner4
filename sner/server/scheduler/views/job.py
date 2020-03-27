# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler job views
"""

import json

from datatables import ColumnDT, DataTables
from flask import redirect, render_template, request, Response, url_for
from sqlalchemy import literal_column
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.scheduler.core import job_delete
from sner.server.scheduler.models import Job, Queue
from sner.server.scheduler.views import blueprint
from sner.server.sqlafilter import filter_parser
from sner.server.utils import SnerJSONEncoder


@blueprint.route('/job/list')
@role_required('operator')
def job_list_route():
    """list jobs"""

    return render_template('scheduler/job/list.html')


@blueprint.route('/job/list.json', methods=['GET', 'POST'])
@role_required('operator')
def job_list_json_route():
    """list jobs, data endpoint"""

    columns = [
        ColumnDT(Job.id, mData='id'),
        ColumnDT(Queue.ident, mData='queue_ident'),
        ColumnDT(Job.assignment, mData='assignment'),
        ColumnDT(Job.retval, mData='retval'),
        ColumnDT(Job.time_start, mData='time_start'),
        ColumnDT(Job.time_end, mData='time_end'),
        ColumnDT((Job.time_end-Job.time_start), mData='time_taken'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Job).outerjoin(Queue)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    jobs = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(jobs, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/job/delete/<job_id>', methods=['GET', 'POST'])
@role_required('operator')
def job_delete_route(job_id):
    """delete job"""

    form = ButtonForm()

    if form.validate_on_submit():
        job_delete(Job.query.get(job_id))
        return redirect(url_for('scheduler.job_list_route'))

    return render_template('button-delete.html', form=form)
