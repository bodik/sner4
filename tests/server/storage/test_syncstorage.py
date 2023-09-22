# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.syncstorage tests
"""

from unittest.mock import Mock, patch

from werkzeug.serving import make_ssl_devcert

import sner.server.storage.elastic
from sner.server.storage.syncstorage import sync_storage


def test_syncstorage(app, tmpworkdir, service, note):  # pylint: disable=unused-argument
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


def test_syncstorage_filter(app, host_factory, note_factory):  # pylint: disable=unused-argument
    """test sync-storage command"""

    host_factory.create(address='127.0.1.1')
    host_factory.create(address='2001:db8::11')
    host2 = host_factory.create(address='127.0.2.1')
    note_factory.create(host=host2, xtype='filteredout')

    indexer_mock = Mock()

    patch_indexer = patch.object(sner.server.storage.syncstorage, 'BulkIndexer', indexer_mock)
    with patch_indexer:
        sync_storage('https://dummy:80', None, None, ['127.0.1.0/24', '2001:db8::/48'])

    indexed_hosts = [x[0][2]['host_address'] for x in indexer_mock.return_value.index.call_args_list]
    assert '127.0.2.1' not in indexed_hosts
    assert '2001:db8::11' in indexed_hosts
