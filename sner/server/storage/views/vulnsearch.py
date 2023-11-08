# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vulnsearch view
"""

from http import HTTPStatus

import json
from datatables import ColumnDT, DataTables
from flask import jsonify, render_template, request, Response
from sqlalchemy import func, inspect, literal_column

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.core import model_annotate, model_tag_multiid
from sner.server.storage.forms import TagMultiidStringyForm
from sner.server.storage.models import Vulnsearch
from sner.server.storage.views import blueprint
from sner.server.utils import filter_query, SnerJSONEncoder


@blueprint.route('/vulnsearch/list')
@session_required('operator')
def vulnsearch_list_route():
    """list vulnsearch"""

    return render_template('storage/vulnsearch/list.html')


@blueprint.route('/vulnsearch/list.json', methods=['GET', 'POST'])
@session_required('operator')
def vulnsearch_list_json_route():
    """list vulnsearch, data endpoint"""

    service_column = func.concat_ws('/', Vulnsearch.service_port, Vulnsearch.service_proto)

    columns = [
        ColumnDT(literal_column('1'), mData='_select', search_method='none', global_search=False),
        ColumnDT(Vulnsearch.id, mData='id'),
        ColumnDT(Vulnsearch.host_id, mData='host_id'),
        ColumnDT(Vulnsearch.host_address, mData='host_address'),
        ColumnDT(Vulnsearch.host_hostname, mData='host_hostname'),
        ColumnDT(Vulnsearch.service_proto, mData='service_proto'),
        ColumnDT(Vulnsearch.service_port, mData='service_port'),
        ColumnDT(service_column, mData='service'),
        ColumnDT(Vulnsearch.via_target, mData='via_target'),
        ColumnDT(Vulnsearch.cveid, mData='cveid'),
        ColumnDT(Vulnsearch.cvss, mData='cvss'),
        ColumnDT(Vulnsearch.cvss3, mData='cvss3'),
        ColumnDT(Vulnsearch.attack_vector, mData='attack_vector'),
        ColumnDT(Vulnsearch.cpe_full, mData='cpe_full'),
        ColumnDT(Vulnsearch.name, mData='name'),
        ColumnDT(Vulnsearch.tags, mData='tags'),
        ColumnDT(Vulnsearch.comment, mData='comment'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(Vulnsearch)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    vulnsearches = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulnsearches, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/vulnsearch/view/<vulnsearch_id>')
@session_required('operator')
def vulnsearch_view_route(vulnsearch_id):
    """view vulnsearch"""

    vulnsearch = Vulnsearch.query.get(vulnsearch_id)
    column_attrs = inspect(Vulnsearch).mapper.column_attrs
    vsearch = {c.key: getattr(vulnsearch, c.key) for c in column_attrs}
    cve_data = vsearch.pop('data')

    return render_template('storage/vulnsearch/view.html', vsearch=vsearch, cve_data=cve_data)


@blueprint.route('/vulnsearch/tag_multiid', methods=['POST'])
@session_required('operator')
def vulnsearch_tag_multiid_route():
    """tag multiple route"""

    form = TagMultiidStringyForm()
    if form.validate_on_submit():
        model_tag_multiid(Vulnsearch, form.action.data, form.tag.data, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/vulnsearch/annotate/<model_id>', methods=['GET', 'POST'])
@session_required('operator')
def vulnsearch_annotate_route(model_id):
    """annotate note"""

    return model_annotate(Vulnsearch, model_id)
