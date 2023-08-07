# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler job views
"""

import json
from datetime import datetime
from http import HTTPStatus

from datatables import ColumnDT, DataTables
from flask import redirect, render_template, request, Response, url_for
from sqlalchemy import func, literal_column

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.scheduler.core import JobManager
from sner.server.scheduler.models import Job, Queue
from sner.server.scheduler.views import blueprint
from sner.server.utils import filter_query, SnerJSONEncoder, json_error_response


@blueprint.route('/job/list')
@session_required('operator')
def job_list_route():
    """list jobs"""

    return render_template('scheduler/job/list.html')


@blueprint.route('/job/list.json', methods=['GET', 'POST'])
@session_required('operator')
def job_list_json_route():
    """list jobs, data endpoint"""

    columns = [
        ColumnDT(Job.id, mData='id'),
        ColumnDT(Queue.name, mData='queue_name'),
        ColumnDT(Job.assignment, mData='assignment'),
        ColumnDT(Job.retval, mData='retval'),
        ColumnDT(Job.time_start, mData='time_start'),
        ColumnDT(Job.time_end, mData='time_end'),
        ColumnDT((func.coalesce(Job.time_end, datetime.utcnow())-Job.time_start), mData='time_taken'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Job).outerjoin(Queue)
    if not (query := filter_query(query, request.values.get('filter'))):
        return json_error_response('Failed to filter query', HTTPStatus.BAD_REQUEST)

    jobs = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(jobs, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/job/delete/<job_id>', methods=['GET', 'POST'])
@session_required('operator')
def job_delete_route(job_id):
    """delete job"""

    form = ButtonForm()

    if form.validate_on_submit():
        try:
            JobManager.delete(Job.query.get(job_id))
            return redirect(url_for('scheduler.job_list_route'))
        except RuntimeError as exc:
            return json_error_response(f'Failed: {exc}', HTTPStatus.INTERNAL_SERVER_ERROR)

    return render_template('button-delete.html', form=form)


@blueprint.route('/job/reconcile/<job_id>', methods=['GET', 'POST'])
@session_required('operator')
def job_reconcile_route(job_id):
    """reconcile job"""

    form = ButtonForm()
    if form.validate_on_submit():
        try:
            JobManager.reconcile(Job.query.get(job_id))
            return redirect(url_for('scheduler.job_list_route'))
        except RuntimeError as exc:
            return json_error_response(f'Failed: {exc}', HTTPStatus.INTERNAL_SERVER_ERROR)

    return render_template('button-generic.html', form=form)


@blueprint.route('/job/repeat/<job_id>', methods=['GET', 'POST'])
@session_required('operator')
def job_repeat_route(job_id):
    """repeat job; requeues targets into same queue, used for rescheduling of failed jobs"""

    form = ButtonForm()

    if form.validate_on_submit():
        JobManager.repeat(Job.query.get(job_id))
        return redirect(url_for('scheduler.job_list_route'))

    return render_template('button-generic.html', form=form)
