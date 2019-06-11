"""authentication handling module"""

from flask import Blueprint, current_app, flash, redirect, request, render_template, url_for
from flask_login import login_user, logout_user

from sner.server import login_manager
from sner.server.form.auth import LoginForm
from sner.server.model.auth import User

blueprint = Blueprint('auth', __name__)  # pylint: disable=invalid-name

import sner.server.controller.auth.user  # noqa: E402,F401  pylint: disable=wrong-import-position


@login_manager.user_loader
def user_loader(user_id):
    """flask_login user loader"""

    return User.query.filter(User.id == user_id).one_or_none()


@blueprint.route('/login', methods=['GET', 'POST'])
def login_route():
    """login route"""

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.active, User.username == form.username.data).one_or_none()
        if user and user.compare_password(form.password.data):
            login_user(user)

            if request.args.get('next'):
                for rule in current_app.url_map.iter_rules():
                    if rule.rule.startswith(request.args.get('next')):
                        return redirect(request.args.get('next'))
            return redirect(url_for('index_route'))

        flash('Invalid credentials', 'error')

    return render_template('auth/login.html', form=form, form_url=url_for('auth.login_route', **request.args))


@blueprint.route('/logout')
def logout_route():
    """logout route"""

    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('index_route'))
