# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vulnsearch core impl
"""

import functools
import json
from hashlib import md5
from http import HTTPStatus
from time import time

import requests
from cpe import CPE
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk
from flask import current_app

from sner.server.storage.models import Note
from sner.server.utils import windowed_query

ES_INDEX = 'vulnsearch'


@functools.lru_cache(maxsize=256)
def cvefor(cpe, cvesearch_url):  # pragma: nocover  ; mocked
    """query cvesearch and filter out response"""

    res = requests.get(f'{cvesearch_url}/api/cvefor/{cpe}')
    if res.status_code != HTTPStatus.OK:
        return []

    # filter unused/oversized data; ex. linux:linux_kernel:xyz is about 800MB
    data = res.json()
    res = None  # free memory
    for cve in data:
        for field in ['vulnerable_configuration', 'vulnerable_configuration_cpe_2_2', 'vulnerable_product']:
            cve.pop(field, None)
    return data


def vulndata(note, parsed_cpe, cve, namelen):
    """project vulndata object"""

    data_id = md5(
        f'{note.host.address}'
        f'|{note.service.proto if note.service else None}'
        f'|{note.service.port if note.service else None}'
        f'|{cve["id"]}'.encode()
    ).hexdigest()

    data = {
        'host_id': note.host_id,
        'service_id': note.service_id,
        'host_address': note.host.address,
        'host_hostname': note.host.hostname,
        'service_proto': note.service.proto if note.service else None,
        'service_port': note.service.port if note.service else None,

        'cveid': cve['id'],
        'name': cve['summary'][:namelen],
        'description': cve['summary'],
        'cvss': cve.get('cvss'),
        'cvss3': cve.get('cvss3'),
        'data': json.dumps(cve),

        'cpe': {
            'full': parsed_cpe.cpe_str,
            'vendor': parsed_cpe.get_vendor()[0],
            'product': parsed_cpe.get_product()[0],
            'version': parsed_cpe.get_version()[0],
            'vendor_product': f'{parsed_cpe.get_vendor()[0]}:{parsed_cpe.get_product()[0]}',
        }
    }

    return data_id, data


class BulkIndexer:
    """elasticsearch bulk indexing buffer"""

    def __init__(self, esclient, buflen=1000):
        self.esclient = esclient
        self.buf = []
        self.buflen = buflen

    def index(self, index, doc_id, doc):
        """index item in buffered way"""

        self.buf.append({'_index': index, '_id': doc_id, '_source': doc})
        if len(self.buf) > self.buflen:
            return self.flush()
        return ()

    def flush(self):
        """flush buffer"""

        res = es_bulk(self.esclient, self.buf)
        self.buf = []
        return res


def update_managed_indices(esclient, current_index):  # pragma: nocover  ; mocked
    """update alias, pune old indices"""

    esclient.indices.put_alias(current_index, ES_INDEX)
    for index in esclient.indices.get(f'{ES_INDEX}-*'):
        if index != current_index:
            esclient.indices.delete(index)


def sync_es_index(cvesearch_url, esd_url, namelen):
    """
    synchronize vulnsearch esd index with cvesearch data for all cpe notes in storage
    """

    esclient = Elasticsearch([esd_url])
    indexer = BulkIndexer(esclient)

    # create new index. there can be new or updated services or cpe notes of
    # existing services, also there might be new or updated cves for cpes the
    # easiest way to handle such complex situation is to create new index and
    # update alias used by the vulnsearch elk ui objects
    current_index = f'{ES_INDEX}-{time()}'

    for note in windowed_query(Note.query.filter(Note.xtype == 'cpe'), Note.id):
        for icpe in json.loads(note.data):
            try:
                parsed_cpe = CPE(icpe)
            except Exception:  # pylint: disable=broad-except  ; library does not provide own core exception class
                current_app.logger.warning(f'invalid cpe, note_id:{note.id} {icpe}')
                continue

            if not parsed_cpe.get_version()[0]:
                continue

            for cve in cvefor(icpe, cvesearch_url):
                data_id, data = vulndata(note, parsed_cpe, cve, namelen)
                indexer.index(current_index, data_id, data)

    indexer.flush()

    # update alias and prune old indexes
    update_managed_indices(esclient, current_index)
    esclient.indices.refresh(current_index)

    # print cache stats
    current_app.logger.debug(f'cvefor cache: {cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect
