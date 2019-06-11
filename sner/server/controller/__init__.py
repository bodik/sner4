"""controllers shared functions"""

from functools import wraps

from flask_login import current_user

from sner.server import login_manager


def role_required(role):
    """flask view decorator implementing role based authorization"""

    def _role_required(fnc):
        @wraps(fnc)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_user.has_role(role):
                return 'Forbidden', 403
            return fnc(*args, **kwargs)
        return decorated_view
    return _role_required
