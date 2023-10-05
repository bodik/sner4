# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.note component
"""

import os
import string

import pytest
from flask import url_for
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from sner.server.extensions import db
from sner.lib import format_host_address
from sner.server.storage.models import Note
from tests.selenium import dt_count_rows, dt_inrow_delete, dt_rendered, dt_wait_processing, webdriver_waituntil
from tests.selenium.storage import (
    check_annotate,
    check_dt_toolbox_freetag,
    check_dt_toolbox_multiactions,
    check_dt_toolbox_select_rows,
    check_dt_toolbox_visibility_toggle,
    check_service_endpoint_dropdown
)


def test_note_list_route(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.note_list_route', _external=True))
    dt_rendered(sl_operator, 'note_list_table', note.comment)


def test_note_list_route_inrow_delete(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """delete note inrow button"""

    note_id = note.id
    db.session.expunge(note)

    sl_operator.get(url_for('storage.note_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'note_list_table')

    assert not Note.query.get(note_id)


def test_note_list_route_annotate(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.note_list_route', _external=True))
    dt_rendered(sl_operator, 'note_list_table', note.comment)
    check_annotate(sl_operator, 'abutton_annotate_dt', note)


def test_note_list_route_service_endpoint_dropdown(live_server, sl_operator, note_factory, service):  # pylint: disable=unused-argument
    """service endpoint uris dropdown test"""

    test_note = note_factory.create(service=service)

    sl_operator.get(url_for('storage.note_list_route', _external=True))
    dt_rendered(sl_operator, 'note_list_table', test_note.comment)
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element(By.ID, 'note_list_table'),
        f'{test_note.service.port}/{test_note.service.proto}'
    )


def test_note_list_route_moredata_dropdown(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """moredata dropdown test"""

    sl_operator.get(url_for('storage.note_list_route', _external=True))
    dt_rendered(sl_operator, 'note_list_table', note.comment)
    sl_operator.find_element(By.ID, 'note_list_table').find_element(
        By.XPATH,
        './/div[contains(@class, "dropdown")]/a[@title="Show more data"]'
    ).click()
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((
        By.XPATH,
        '//table[@id="note_list_table"]//h6[text()="More data"]'
    )))


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='ux tested by host_list')
def test_note_list_route_selectrows(live_server, sl_operator, notes_multiaction):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    check_dt_toolbox_select_rows(sl_operator, 'storage.note_list_route', 'note_list_table')


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='ux tested by host_list')
def test_note_list_route_dt_toolbox_multiactions(live_server, sl_operator, notes_multiaction):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    check_dt_toolbox_multiactions(sl_operator, 'storage.note_list_route', 'note_list_table', Note)


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='ux tested by host_list')
def test_note_list_route_dt_toolbox_freetag(live_server, sl_operator, notes_multiaction):  # pylint: disable=unused-argument
    """test dt freetag buttons"""

    check_dt_toolbox_freetag(sl_operator, 'storage.note_list_route', 'note_list_table', Note)


@pytest.mark.skipif('PYTEST_SLOW' not in os.environ, reason='ux tested by host_list')
def test_note_list_route_dt_toolbox_visibility_toggle(live_server, sl_operator, note_factory):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    check_dt_toolbox_visibility_toggle(sl_operator, 'storage.note_list_route', 'note_list_table', note_factory)


def test_note_view_route_annotate(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """test note annotation from view route"""

    sl_operator.get(url_for('storage.note_view_route', note_id=note.id, _external=True))
    check_annotate(sl_operator, 'abutton_annotate_view', note)


def test_note_view_route_service_endpoint_dropdown(live_server, sl_operator, note_factory, service):  # pylint: disable=unused-argument
    """test note annotation from view route"""

    test_note = note_factory.create(service=service)

    sl_operator.get(url_for('storage.note_view_route', note_id=test_note.id, _external=True))
    check_service_endpoint_dropdown(
        sl_operator,
        sl_operator.find_element(By.XPATH, '//td[contains(@class, "service_endpoint_dropdown")]'),
        f'<Service {test_note.service.id}: {format_host_address(test_note.host.address)} {test_note.service.proto}.{test_note.service.port}>'
    )


def test_note_view_route_moredata_dropdown(live_server, sl_operator, note):  # pylint: disable=unused-argument
    """test note view breadcrumb ribbon moredata dropdown"""

    sl_operator.get(url_for('storage.note_view_route', note_id=note.id, _external=True))
    sl_operator.find_element(By.XPATH, '//div[contains(@class, "breadcrumb-buttons")]').find_element(
        By.XPATH,
        './/div[contains(@class, "dropdown")]/a[@title="Show more data"]'
    ).click()
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((
        By.XPATH,
        '//div[contains(@class, "breadcrumb-buttons")]//h6[text()="More data"]'
    )))


def test_note_grouped_route_filter_specialchars(live_server, sl_operator, note_factory):  # pylint: disable=unused-argument
    """test grouped note info view and filtering features with specialchars"""

    note_factory.create(xtype=string.printable)

    sl_operator.get(url_for('storage.note_grouped_route', _external=True))
    elem_xpath = f"//a[contains(text(), '{string.digits}')]"
    webdriver_waituntil(sl_operator, EC.visibility_of_element_located((By.XPATH, elem_xpath)))

    sl_operator.find_element(By.XPATH, elem_xpath).click()
    dt_wait_processing(sl_operator, 'note_list_table')

    assert dt_count_rows(sl_operator, 'note_list_table') == 1
