# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.versioninfo component
"""

from flask import url_for

from sner.server.storage.models import Vulnsearch

from tests.selenium import dt_rendered
from tests.selenium.storage import (
    check_annotate,
    check_dt_toolbox_freetag,
    check_dt_toolbox_multiactions,
    check_dt_toolbox_select_rows,
)


def test_vulnsearch_list_route(live_server, sl_operator, vulnsearch):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.vulnsearch_list_route', _external=True))
    dt_rendered(sl_operator, 'vulnsearch_list_table', vulnsearch.name)


def test_vulnsearch_list_route_annotate(live_server, sl_operator, vulnsearch):  # pylint: disable=unused-argument
    """test annotation from list route"""

    sl_operator.get(url_for('storage.vulnsearch_list_route', _external=True))
    dt_rendered(sl_operator, 'vulnsearch_list_table', vulnsearch.name)
    check_annotate(sl_operator, 'abutton_annotate_dt', vulnsearch)


def test_vulnsearch_list_route_selectrows(live_server, sl_operator, vulnsearch_multiaction):  # pylint: disable=unused-argument
    """test dt selection and selection buttons"""

    check_dt_toolbox_select_rows(sl_operator, 'storage.vulnsearch_list_route', 'vulnsearch_list_table')


def test_vulnsearch_list_route_dt_toolbox_multiactions(live_server, sl_operator, vulnsearch_multiaction):  # pylint: disable=unused-argument
    """test vulnsearchs multiactions"""

    check_dt_toolbox_multiactions(sl_operator, 'storage.vulnsearch_list_route', 'vulnsearch_list_table', Vulnsearch, test_delete=False)


def test_vulnsearch_list_route_dt_toolbox_freetag(live_server, sl_operator, vulnsearch_multiaction):  # pylint: disable=unused-argument
    """test dt freetag buttons"""

    check_dt_toolbox_freetag(sl_operator, 'storage.vulnsearch_list_route', 'vulnsearch_list_table', Vulnsearch)
