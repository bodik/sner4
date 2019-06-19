"""authentication handling module"""

from functools import wraps
from http import HTTPStatus

from flask import _request_ctx_stack, Blueprint, current_app, flash, g, redirect, request, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from sner.server import login_manager
from sner.server.form.auth import LoginForm
from sner.server.model.auth import User
from sner.server.password_supervisor import PasswordSupervisor as PWS


blueprint = Blueprint('auth', __name__)  # pylint: disable=invalid-name


def role_required(role, api=False):
    """flask view decorator implementing role based authorization; does not redirect to login for api views/routes"""

    def _role_required(fnc):
        @wraps(fnc)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                if api:
                    return 'Unauthorized', HTTPStatus.UNAUTHORIZED
                return login_manager.unauthorized()

            if not current_user.has_role(role):
                return 'Forbidden', HTTPStatus.FORBIDDEN

            return fnc(*args, **kwargs)

        return decorated_view
    return _role_required


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
        if user and PWS.compare(PWS.hash(form.password.data, PWS.get_salt(user.password)), user.password):
            _request_ctx_stack.top.session = current_app.session_interface.new_session()
            if hasattr(g, 'csrf_token'):  # cleanup g, which is used by flask_wtf
                delattr(g, 'csrf_token')
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
    session.clear()
    return redirect(url_for('index_route'))


import sner.server.controller.auth.user  # noqa: E402,F401  pylint: disable=wrong-import-position
