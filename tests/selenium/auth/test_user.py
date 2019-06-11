"""selenium ui tests for auth.user component"""

from flask import url_for

from sner.server.model.auth import User
from tests.selenium import dt_inrow_delete, dt_rendered


def test_user_list_route(live_server, sl_admin, test_user):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_admin.get(url_for('auth.user_list_route', _external=True))
    dt_rendered(sl_admin, 'user_list_table', test_user.username)


def test_user_list_route_inrow_delete(live_server, sl_admin, test_user):  # pylint: disable=unused-argument
    """delete user inrow button"""

    sl_admin.get(url_for('auth.user_list_route', _external=True))
    # in this test-case there are multiple items in the table (current_user, test_user), hence index which to delete has to be used
    dt_inrow_delete(sl_admin, 'user_list_table', 1)
    assert not User.query.filter(User.id == test_user.id).one_or_none()
