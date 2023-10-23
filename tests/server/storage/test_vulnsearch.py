# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

import functools
from unittest.mock import Mock, patch

from flask import current_app
from werkzeug.serving import make_ssl_devcert

import sner.server.storage.elastic
from sner.server.storage.models import Vulnsearch
from sner.server.storage.vulnsearch import get_attack_vector, VulnsearchManager


def test_get_attack_vector():
    """test get_attack_vector helper"""

    assert get_attack_vector({'exploitability3': {'attackvector': 'DUMMY'}}) == 'DUMMY'
    assert get_attack_vector({'access': {'vector': 'DUMMY'}}) == 'DUMMY'
    assert get_attack_vector({}) is None


def test_rebuild_elastic(app, tmpworkdir, note_factory):  # pylint: disable=unused-argument
    """test rebuild_elastic command"""

    # ? cache is not used in the test, but mock is required to have same prototype
    @functools.lru_cache(maxsize=256)
    def cvefor_mock(_1, _2):
        """
        mock external cvesearch service.
        note: function prototype should match original so the cache stats debug code does not break.
        """

        return [{
            'id': 'CVE-0000-0000',
            'summary': 'mock summary',
            'cvss': 0.0,
            'exploitability3': {'attackvector': 'NETWORK'}
        }]

    es_bulk_mock = Mock()
    update_alias_mock = Mock()
    cert, key = make_ssl_devcert('testcert')
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor2:product2"]')
    note_factory.create_batch(1000, xtype='cpe', data='["cpe:/a:vendor3:product3:0.0"]')
    note_factory.create(xtype='cpe', data='["invalid"]')

    patch_cvefor = patch.object(sner.server.storage.vulnsearch.VulnsearchManager, 'cvefor', cvefor_mock)
    patch_esbulk = patch.object(sner.server.storage.elastic, 'es_bulk', es_bulk_mock)
    patch_update = patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    with patch_cvefor, patch_esbulk, patch_update:
        VulnsearchManager('https://dummy:80', key, cert).rebuild_elastic('https://dummy:80')

    assert es_bulk_mock.call_count == 2
    update_alias_mock.assert_called_once()


def test_rebuild_elastic_filter(app, host_factory, note_factory):  # pylint: disable=unused-argument
    """test sync-vunsearch with filter command"""

    note_factory.create(host=host_factory.create(address='127.0.1.1'), xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')
    note_factory.create(host=host_factory.create(address='127.0.2.1'), xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')
    note_factory.create(host=host_factory.create(address='2001:db8::11'), xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')

    cvefor_mock = Mock(return_value=[{
        'id': 'CVE-0000-0000',
        'summary': 'mock summary',
        'cvss': 0.0,
        'exploitability3': {'attackvector': 'NETWORK'}
    }])
    indexer_mock = Mock()

    patch_cvefor = patch.object(sner.server.storage.vulnsearch.VulnsearchManager, 'cvefor', cvefor_mock)
    patch_indexer = patch.object(sner.server.storage.vulnsearch, 'BulkIndexer', indexer_mock)
    with patch_cvefor, patch_indexer:
        VulnsearchManager('https://dummy:80').rebuild_elastic('https://dummy:80', ['127.0.1.0/24', '2001:db8::/48'])

    indexed_hosts = [x[0][2]['host_address'] for x in indexer_mock.return_value.index.call_args_list]
    assert '127.0.2.1' not in indexed_hosts
    assert '2001:db8::11' in indexed_hosts


def test_rebuild_localdb(app, note_factory):  # pylint: disable=unused-argument
    """test rebuild localdb"""

    current_app.config['SNER_VULNSEARCH_REBUILD_BUFLEN'] = 0
    note_factory.create(xtype='cpe', data='["cpe:/a:vendor1:product1:0.0"]')

    cvefor_mock = Mock(return_value=[{
        'id': 'CVE-0000-0000',
        'summary': 'mock summary',
        'cvss': 0.0,
        'exploitability3': {'attackvector': 'NETWORK'}
    }])

    patch_cvefor = patch.object(sner.server.storage.vulnsearch.VulnsearchManager, 'cvefor', cvefor_mock)
    with patch_cvefor:
        VulnsearchManager('https://dummy:80').rebuild_localdb()

    assert Vulnsearch.query.count() == 1
