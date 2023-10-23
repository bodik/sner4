# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vulnsearch view
"""

from http import HTTPStatus

import json
from datatables import ColumnDT, DataTables
from flask import jsonify, render_template, request, Response
from sqlalchemy import func

from sner.server.auth.core import session_required
from sner.server.extensions import db
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

    columns = [
        ColumnDT(Vulnsearch.id, mData='id'),
        ColumnDT(Vulnsearch.host_id, mData='host_id'),
        ColumnDT(Vulnsearch.host_address, mData='host_address'),
        ColumnDT(Vulnsearch.host_hostname, mData='host_hostname'),
        ColumnDT(Vulnsearch.service_proto, mData='service_proto'),
        ColumnDT(Vulnsearch.service_port, mData='service_port'),
        ColumnDT(func.concat_ws('/', Vulnsearch.service_port, Vulnsearch.service_proto), mData='service'),
        ColumnDT(Vulnsearch.via_target, mData='via_target'),
        ColumnDT(Vulnsearch.cveid, mData='cveid'),
        ColumnDT(Vulnsearch.cvss, mData='cvss'),
        ColumnDT(Vulnsearch.cvss3, mData='cvss3'),
        ColumnDT(Vulnsearch.attack_vector, mData='attack_vector'),
        ColumnDT(Vulnsearch.cpe['full'], mData='cpe'),
        ColumnDT(Vulnsearch.name, mData='name'),
    ]
    query = db.session.query().select_from(Vulnsearch)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    vulnsearches = DataTables(request.values.to_dict(), query, columns).output_result()
    return Response(json.dumps(vulnsearches, cls=SnerJSONEncoder), mimetype='application/json')
