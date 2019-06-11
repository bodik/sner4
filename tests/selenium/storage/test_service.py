"""selenium ui tests for storage.service component"""

from flask import url_for

from sner.server.model.storage import Service
from tests.selenium import dt_inrow_delete, dt_rendered


def test_service_list_route(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', test_service.comment)


def test_service_list_route_inrow_delete(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """delete service inrow button"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'service_list_table')
    assert not Service.query.filter(Service.id == test_service.id).one_or_none()
