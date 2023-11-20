# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.commands tests
"""

from unittest.mock import Mock, patch

from flask import current_app
from werkzeug.serving import make_ssl_devcert

import sner.server.storage.elastic
from sner.server.storage.models import Vulnsearch
from sner.server.storage.vulnsearch import get_attack_vector, cpe_notes, VulnsearchManager


def test_get_attack_vector():
    """test get_attack_vector helper"""

    assert get_attack_vector({'exploitability3': {'attackvector': 'DUMMY'}}) == 'DUMMY'
    assert get_attack_vector({'access': {'vector': 'DUMMY'}}) == 'DUMMY'
    assert get_attack_vector({}) is None


def test_cpe_notes(app, note_factory):  # pylint: disable=unused-argument
    """test cpe_notes edge cases"""

    note_factory.create(xtype='cpe', data='["cpe:/a:vendor2:product2"]')
    note_factory.create(xtype='cpe', data='["invalid"]')

    assert not list(cpe_notes())


def test_rebuild_elastic(app, tmpworkdir, vulnsearch):  # pylint: disable=unused-argument
    """test vulnsearch rebuild_elastic"""

    es_bulk_mock = Mock()
    update_alias_mock = Mock()
    cert, key = make_ssl_devcert('testcert')
    current_app.config['SNER_VULNSEARCH_REBUILD_BUFLEN'] = 0

    with (
        patch.object(sner.server.storage.elastic, 'es_bulk', es_bulk_mock),
        patch.object(sner.server.storage.elastic.BulkIndexer, 'initialize', Mock()),
        patch.object(sner.server.storage.elastic.BulkIndexer, 'update_alias', update_alias_mock)
    ):
        VulnsearchManager('https://dummy:80', key, cert).rebuild_elastic('https://dummy:80')

    assert es_bulk_mock.call_count == 2
    update_alias_mock.assert_called_once()


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
