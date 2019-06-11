"""selenium ui tests for scheduler.excl component"""

from flask import url_for

from sner.server.model.scheduler import Excl
from tests.selenium import dt_inrow_delete, dt_rendered


def test_excl_list_route(live_server, sl_operator, test_excl_network):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.excl_list_route', _external=True))
    dt_rendered(sl_operator, 'excl_list_table', test_excl_network.comment)


def test_excl_list_route_inrow_delete(live_server, sl_operator, test_excl_network):  # pylint: disable=unused-argument
    """delete excl inrow button"""

    sl_operator.get(url_for('scheduler.excl_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'excl_list_table')
    assert not Excl.query.filter(Excl.id == test_excl_network.id).one_or_none()
