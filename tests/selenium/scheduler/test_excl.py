"""selenium ui tests for scheduler.excl component"""

from flask import url_for

from sner.server.model.scheduler import Excl
from tests.selenium import dt_inrow_delete, dt_rendered


def test_excl_list_route(live_server, selenium, test_excl_network):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    selenium.get(url_for('scheduler.excl_list_route', _external=True))
    dt_rendered(selenium, 'excl_list_table', test_excl_network.comment)


def test_excl_list_route_inrow_delete(live_server, selenium, test_excl_network):  # pylint: disable=unused-argument
    """delete excl inrow button"""

    selenium.get(url_for('scheduler.excl_list_route', _external=True))
    dt_inrow_delete(selenium, 'excl_list_table')
    assert not Excl.query.filter(Excl.id == test_excl_network.id).one_or_none()
