# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
selenium ui tests for storage.versioninfo component
"""

from flask import url_for

from tests.selenium import dt_rendered


def test_vulnsearch_list_route(live_server, sl_operator, vulnsearch):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('storage.vulnsearch_list_route', _external=True))
    dt_rendered(sl_operator, 'vulnsearch_list_table', vulnsearch.cveid)
