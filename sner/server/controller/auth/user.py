"""controller auth.user"""

from datatables import ColumnDT, DataTables
from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy_filters import apply_filters

from sner.server import db
from sner.server.controller import role_required
from sner.server.controller.auth import blueprint
from sner.server.form import ButtonForm
from sner.server.form.auth import UserForm, UserChangePasswordForm
from sner.server.model.auth import User
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
        ColumnDT(User.roles, mData='roles'),
        ColumnDT(User.active, mData='active'),
        ColumnDT('1', mData='_buttons', search_method='none', global_search=False)
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

    return render_template('auth/user/addedit.html', form=form, form_url=url_for('auth.user_add_route'))


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

    return render_template('auth/user/addedit.html', form=form, form_url=url_for('auth.user_edit_route', user_id=user_id))


@blueprint.route('/user/delete/<user_id>', methods=['GET', 'POST'])
@role_required('admin')
def user_delete_route(user_id):
    """delete user"""

    user = User.query.get(user_id)
    form = ButtonForm()

    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('auth.user_list_route'))

    return render_template('button-delete.html', form=form, form_url=url_for('auth.user_delete_route', user_id=user_id))


@blueprint.route('/user/changepassword', methods=['GET', 'POST'])
@role_required('user')
def user_changepassword_route():
    """change password for self"""

    form = UserChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.filter(User.id == current_user.id).one()
        user.password = form.password1.data
        db.session.commit()
        flash('Password changed.', 'info')
        return redirect(url_for('auth.user_changepassword_route'))

    return render_template('auth/user/changepassword.html', form=form, form_url=url_for('auth.user_changepassword_route'))
