# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.syncstorage tests
"""

from unittest.mock import Mock, patch

from werkzeug.serving import make_ssl_devcert

import sner.server.storage.elastic
from sner.server.storage.syncstorage import sync_storage


def test_syncvulnsearch(app, tmpworkdir, service, note):  # pylint: disable=unused-argument
    """test sync-storage command"""

    es_bulk_mock = Mock()
    update_alias_mock = Mock()
    cert, key = make_ssl_devcert('testcert')

    patch_esbulk = patch.object(sner.server.storage.elastic, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    with patch_esbulk, patch_update:
        sync_storage('https://dummy:80', key, cert)

    es_bulk_mock.assert_called()
    update_alias_mock.assert_called()
