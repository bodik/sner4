# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth user views; user management
"""

from http import HTTPStatus

from datatables import ColumnDT, DataTables
from flask import jsonify, redirect, render_template, request, url_for
from sqlalchemy import literal_column
from sqlalchemy_filters import apply_filters

from sner.server.auth.core import role_required
from sner.server.auth.forms import UserForm
from sner.server.auth.models import User
from sner.server.auth.views import blueprint
from sner.server.extensions import db
from sner.server.forms import ButtonForm
from sner.server.password_supervisor import PasswordSupervisor as PWS
from sner.server.sqlafilter import filter_parser


@blueprint.route('/user/list')
@role_required('admin')
def user_list_route():
    """list users"""

    return render_template('auth/user/list.html')


@blueprint.route('/user/list.json', methods=['GET', 'POST'])
@role_required('admin')
def user_list_json_route():
    """list users, data endpoint"""

    columns = [
        ColumnDT(User.id, mData='id'),
        ColumnDT(User.username, mData='username'),
        ColumnDT(User.email, mData='email'),
        ColumnDT(User.apikey.isnot(None), mData='apikey'),  # pylint: disable=no-member
        ColumnDT(User.roles, mData='roles'),
        ColumnDT(User.active, mData='active'),
        ColumnDT(literal_column('1'), mData='_buttons', search_method='none', global_search=False)
    ]
    query = db.session.query().select_from(User)
    if 'filter' in request.values:
        query = apply_filters(query, filter_parser.parse(request.values.get('filter')), do_auto_join=False)

    users = DataTables(request.values.to_dict(), query, columns).output_result()
    return jsonify(users)


@blueprint.route('/user/add', methods=['GET', 'POST'])
@role_required('admin')
def user_add_route():
    """add user"""

    form = UserForm()

    if form.validate_on_submit():
        user = User()
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('auth.user_list_route'))

    return render_template('auth/user/addedit.html', form=form)


@blueprint.route('/auth/edit/<user_id>', methods=['GET', 'POST'])
@role_required('admin')
def user_edit_route(user_id):
    """edit task"""

    user = User.query.get(user_id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        return redirect(url_for('auth.user_list_route'))

    return render_template('auth/user/addedit.html', form=form)


@blueprint.route('/user/delete/<user_id>', methods=['GET', 'POST'])
@role_required('admin')
def user_delete_route(user_id):
    """delete user"""

    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(User.query.get(user_id))
        db.session.commit()
        return redirect(url_for('auth.user_list_route'))

    return render_template('button-delete.html', form=form)


@blueprint.route('/user/apikey/<user_id>/<action>', methods=['POST'])
@role_required('admin')
def user_apikey_route(user_id, action):
    """manage apikey for user"""

    user = User.query.get(user_id)
    form = ButtonForm()
    if user and form.validate_on_submit():

        if action == 'generate':
            apikey = PWS.generate_apikey()
            user.apikey = apikey
            db.session.commit()
            return jsonify({'title': 'Apikey operation', 'detail': 'New apikey generated: %s' % apikey}), HTTPStatus.OK

        if action == 'revoke':
            user.apikey = None
            db.session.commit()
            return jsonify({'title': 'Apikey operation', 'detail': 'Apikey revoked'}), HTTPStatus.OK

    return jsonify({'title': 'Apikey operation', 'detail': 'Invalid request'}), HTTPStatus.BAD_REQUEST
