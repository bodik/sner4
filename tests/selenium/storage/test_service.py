"""selenium ui tests for storage.service component"""

from sner.server.model.storage import Service
from tests.selenium import dt_inrow_delete, dt_rendered


def test_list(live_server, selenium, test_service):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    dt_rendered(selenium, 'storage.service_list_route', 'service_list_table', test_service.comment)


def test_list_inrow_delete(live_server, selenium, test_service):  # pylint: disable=unused-argument
    """delete service inrow button"""

    dt_inrow_delete(selenium, 'storage.service_list_route', 'service_list_table')
    assert not Service.query.filter(Service.id == test_service.id).one_or_none()
