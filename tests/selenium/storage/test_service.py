# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.service component
"""

from flask import url_for

from sner.server.storage.models import Service
from tests.selenium import dt_inrow_delete, dt_rendered
from tests.selenium.storage import check_annotate


def test_service_list_route(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', test_service.comment)


def test_service_list_route_inrow_delete(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """delete service inrow button"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'service_list_table')
    assert not Service.query.get(test_service.id)


def test_service_list_route_annotate(live_server, sl_operator, test_service):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', test_service.comment)
    check_annotate(sl_operator, 'abutton_annotate_dt', test_service)
