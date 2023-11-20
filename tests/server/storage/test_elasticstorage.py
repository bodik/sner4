# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.syncstorage tests
"""

from unittest.mock import Mock, patch

from werkzeug.serving import make_ssl_devcert

import sner.server.storage.elastic
from sner.server.storage.elasticstorage import ElasticStorageManager


def test_rebuild_elasticstorage(app, tmpworkdir, service, note):  # pylint: disable=unused-argument
    """test sync-storage command"""

    es_bulk_mock = Mock()
    update_alias_mock = Mock()
    cert, key = make_ssl_devcert('testcert')

    patch_esbulk = patch.object(sner.server.storage.elastic, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    with patch_esbulk, patch_update:
        ElasticStorageManager('https://dummy:80', key, cert).rebuild()

    es_bulk_mock.assert_called()
    update_alias_mock.assert_called()
