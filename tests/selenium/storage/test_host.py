"""selenium ui tests for storage.host component"""

from sner.server.model.storage import Host
from tests.selenium import dt_inrow_delete, dt_rendered


def test_list(live_server, selenium, test_host):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    dt_rendered(selenium, 'storage.host_list_route', 'host_list_table', test_host.comment)


def test_list_inrow_delete(live_server, selenium, test_host):  # pylint: disable=unused-argument
    """delete host inrow button"""

    dt_inrow_delete(selenium, 'storage.host_list_route', 'host_list_table')
    assert not Host.query.filter(Host.id == test_host.id).one_or_none()
