# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage versioninfo view
"""

from http import HTTPStatus

import json
from datatables import ColumnDT, DataTables
from flask import jsonify, render_template, request, Response
from sqlalchemy import func

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.forms import VersionInfoQueryForm
from sner.server.storage.models import VersionInfo
from sner.server.storage.version_parser import is_in_version_range, parse as versionspec_parse
from sner.server.storage.views import blueprint
from sner.server.utils import filter_query, SnerJSONEncoder


@blueprint.route('/versioninfo/list')
@session_required('operator')
def versioninfo_list_route():
    """list versioninfos"""

    return render_template(
        'storage/versioninfo/list.html',
        form=VersionInfoQueryForm(request.values)
    )


@blueprint.route('/versioninfo/list.json', methods=['GET', 'POST'])
@session_required('operator')
def versioninfo_list_json_route():
    """list versioninfo, data endpoint"""

    columns = [
        ColumnDT(VersionInfo.id, mData='id'),
        ColumnDT(VersionInfo.host_id, mData='host_id'),
        ColumnDT(VersionInfo.host_address, mData='host_address'),
        ColumnDT(VersionInfo.host_hostname, mData='host_hostname'),
        ColumnDT(VersionInfo.service_proto, mData='service_proto'),
        ColumnDT(VersionInfo.service_port, mData='service_port'),
        ColumnDT(func.concat_ws('/', VersionInfo.service_port, VersionInfo.service_proto), mData='service'),
        ColumnDT(VersionInfo.via_target, mData='via_target'),
        ColumnDT(VersionInfo.product, mData='product'),
        ColumnDT(VersionInfo.version, mData='version'),
        ColumnDT(func.text(VersionInfo.extra), mData='extra'),
    ]
    query = db.session.query().select_from(VersionInfo)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    if request.values.get('product'):
        query = query.filter(VersionInfo.product.ilike(f"%{request.values.get('product')}%"))

    versioninfos = DataTables(request.values.to_dict(), query, columns).output_result()

    if request.values.get('versionspec'):
        parsed_version_specifier = versionspec_parse(request.values.get('versionspec'))
        versioninfos["data"] = list(filter(
            lambda item: is_in_version_range(item["version"], parsed_version_specifier),
            versioninfos["data"]
        ))
        versioninfos["recordsFiltered"] = len(versioninfos["data"])

    return Response(json.dumps(versioninfos, cls=SnerJSONEncoder), mimetype='application/json')
