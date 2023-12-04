# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage versioninfo view
"""

from http import HTTPStatus

import json
from datatables import ColumnDT, DataTables
from flask import jsonify, render_template, request, Response
from sqlalchemy import func, literal_column

from sner.server.auth.core import session_required
from sner.server.extensions import db
from sner.server.storage.core import model_annotate, model_tag_multiid
from sner.server.storage.forms import TagMultiidStringyForm, VersioninfoQueryForm
from sner.server.storage.models import Versioninfo
from sner.server.storage.version_parser import is_in_version_range, parse as versionspec_parse
from sner.server.storage.views import blueprint
from sner.server.utils import filter_query, SnerJSONEncoder


@blueprint.route('/versioninfo/list')
@session_required('operator')
def versioninfo_list_route():
    """list versioninfos"""

    return render_template(
        'storage/versioninfo/list.html',
        form=VersioninfoQueryForm(request.values)
    )


@blueprint.route('/versioninfo/list.json', methods=['GET', 'POST'])
@session_required('operator')
def versioninfo_list_json_route():
    """list versioninfo, data endpoint"""

    service_column = func.concat_ws('/', Versioninfo.service_port, Versioninfo.service_proto)

    columns = [
        ColumnDT(literal_column('1'), mData='_select', search_method='none', global_search=False),
        ColumnDT(Versioninfo.id, mData='id'),
        ColumnDT(Versioninfo.host_id, mData='host_id'),
        ColumnDT(Versioninfo.host_address, mData='host_address'),
        ColumnDT(Versioninfo.host_hostname, mData='host_hostname'),
        ColumnDT(Versioninfo.service_proto, mData='service_proto'),
        ColumnDT(Versioninfo.service_port, mData='service_port'),
        ColumnDT(service_column, mData='service'),
        ColumnDT(Versioninfo.via_target, mData='via_target'),
        ColumnDT(Versioninfo.product, mData='product'),
        ColumnDT(Versioninfo.version, mData='version'),
        ColumnDT(func.text(Versioninfo.extra), mData='extra'),
        ColumnDT(Versioninfo.tags, mData='tags'),
        ColumnDT(Versioninfo.comment, mData='comment'),
    ]
    query = db.session.query().select_from(Versioninfo)
    if not (query := filter_query(query, request.values.get('filter'))):
        return jsonify({'message': 'Failed to filter query'}), HTTPStatus.BAD_REQUEST

    if request.values.get('product'):
        query = query.filter(Versioninfo.product.ilike(f"%{request.values.get('product')}%"))

    # pre-query, fake server side paging
    request_values = request.values.to_dict()
    orig_start = int(request_values.get('start', '0'))
    orig_length = int(request_values.get('length', '-1'))
    request_values.update({'start': '0', 'length': '-1'})

    versioninfos = DataTables(request_values, query, columns).output_result()

    if request_values.get('versionspec'):
        parsed_version_specifier = versionspec_parse(request_values.get('versionspec'))
        versioninfos["data"] = list(filter(
            lambda item: is_in_version_range(item["version"], parsed_version_specifier),
            versioninfos["data"]
        ))
        versioninfos["recordsFiltered"] = len(versioninfos["data"])

    # post-query, fake server side paging
    if orig_start > 0:
        versioninfos["data"] = versioninfos["data"][orig_start:]
    if orig_length >= 0:
        versioninfos["data"] = versioninfos["data"][:orig_length]

    return Response(json.dumps(versioninfos, cls=SnerJSONEncoder), mimetype='application/json')


@blueprint.route('/versioninfo/tag_multiid', methods=['POST'])
@session_required('operator')
def versioninfo_tag_multiid_route():
    """tag multiple route"""

    form = TagMultiidStringyForm()
    if form.validate_on_submit():
        model_tag_multiid(Versioninfo, form.action.data, form.tag.data, [tmp.data for tmp in form.ids.entries])
        return '', HTTPStatus.OK
    return jsonify({'message': 'Invalid form submitted.'}), HTTPStatus.BAD_REQUEST


@blueprint.route('/versioninfo/annotate/<model_id>', methods=['GET', 'POST'])
@session_required('operator')
def versioninfo_annotate_route(model_id):
    """annotate note"""

    return model_annotate(Versioninfo, model_id)
