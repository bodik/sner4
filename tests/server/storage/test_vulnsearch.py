# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import functools
from unittest.mock import Mock, patch

from werkzeug.serving import make_ssl_devcert

import sner.server.storage.vulnsearch
from sner.server.storage.vulnsearch import sync_vulnsearch


def test_syncvulnsearch(app, tmpworkdir, note_factory):  # pylint: disable=unused-argument
    """test sync-vulnsearch command"""

    # ? cache is not used in the test, but mock is required to have same prototype
    @functools.lru_cache(maxsize=256)
    def cvefor_mock(_1, _2, _3, _4):
        """
        mock external cvesearch service.
        note: function prototype should match original so the cache stats debug code does not break.
        """

        return [{
            'id': 'CVE-0000-0000',
            'summary': 'mock summary',
            'cvss': 0.0,
        }]

    es_bulk_mock = Mock()
    update_managed_indices_mock = Mock()
    cert, key = make_ssl_devcert('testcert')
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor2:product2"]')
    note_factory.create_batch(1000, xtype='cpe', data='["cpe:/a:vendor3:product3:0.0"]')
    note_factory.create(xtype='cpe', data='["invalid"]')

    patch_cvefor = patch.object(sner.server.storage.vulnsearch, 'cvefor', cvefor_mock)
    patch_esbulk = patch.object(sner.server.storage.vulnsearch, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.vulnsearch, 'update_managed_indices', update_managed_indices_mock)
    with patch_cvefor, patch_esbulk, patch_update:
        sync_vulnsearch('https://dummy:80', 'https://dummy:80', 10, key, cert)

    assert es_bulk_mock.call_count == 2
    update_managed_indices_mock.assert_called_once()
