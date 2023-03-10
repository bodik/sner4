# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.syncstorage tests
"""

from unittest.mock import Mock, patch

from werkzeug.serving import make_ssl_devcert

import sner.server.storage.syncstorage
from sner.server.storage.syncstorage import sync_storage


def test_syncvulnsearch(app, tmpworkdir, note):  # pylint: disable=unused-argument
    """test sync-storage command"""

    es_bulk_mock = Mock()
    update_managed_indices_mock = Mock()
    cert, key = make_ssl_devcert('testcert')

    patch_esbulk = patch.object(sner.server.storage.vulnsearch, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.syncstorage, 'update_managed_indices', update_managed_indices_mock)
    with patch_esbulk, patch_update:
        sync_storage('https://dummy:80', key, cert)

    assert es_bulk_mock.call_count == 1
    update_managed_indices_mock.assert_called_once()
