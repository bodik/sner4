# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.service component
"""

from flask import url_for
from selenium.webdriver.common.by import By

from sner.server.extensions import db
from sner.server.storage.models import Service
from tests.selenium import dt_inrow_delete, dt_rendered
from tests.selenium.storage import check_annotate, check_service_endpoint_dropdown


def test_service_list_route(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', service.comment)


def test_service_list_route_inrow_delete(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """delete service inrow button"""

    service_id = service.id
    db.session.expunge(service)

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'service_list_table')

    assert not Service.query.get(service_id)


def test_service_list_route_annotate(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', service.comment)
    check_annotate(sl_operator, 'abutton_annotate_dt', service)


def test_service_list_route_service_endpoint_dropdown(live_server, sl_operator, service):  # pylint: disable=unused-argument
    """service endpoint uris dropdown test"""

    sl_operator.get(url_for('storage.service_list_route', _external=True))
    dt_rendered(sl_operator, 'service_list_table', service.comment)
    check_service_endpoint_dropdown(sl_operator, sl_operator.find_element(By.ID, 'service_list_table'), service.port)
