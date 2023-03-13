# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vulnsearch core impl
"""

import functools
import json
import ssl
import warnings
from datetime import datetime
from hashlib import md5
from http import HTTPStatus

import requests
from cpe import CPE
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchWarning
from elasticsearch.helpers import bulk as es_bulk
from flask import current_app

from sner.server.storage.models import Note
from sner.server.utils import windowed_query


def ignore_warning(category):
    """ignore warning decorator"""
    def _ignore_warning(function):
        @functools.wraps(function)
        def __ignore_warning(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=category)
                result = function(*args, **kwargs)
            return result
        return __ignore_warning
    return _ignore_warning


@functools.lru_cache(maxsize=256)
def cvefor(cpe, cvesearch_url, tlsauth_key, tlsauth_cert):  # pragma: nocover  ; mocked
    """query cvesearch and filter out response"""

    res = requests.get(f'{cvesearch_url}/api/cvefor/{cpe}', cert=(tlsauth_cert, tlsauth_key))
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

    @ignore_warning(ElasticsearchWarning)
    def flush(self):
        """flush buffer"""

        res = es_bulk(self.esclient, self.buf)
        self.buf = []
        return res


@ignore_warning(ElasticsearchWarning)
def update_managed_indices(esclient, current_index, alias):  # pragma: nocover  ; mocked
    """update alias, pune old indices"""

    esclient.indices.put_alias(index=current_index, name=alias)
    for item in esclient.indices.get(index=f'{alias}-*'):
        if item != current_index:
            esclient.indices.delete(index=item)
    esclient.indices.refresh(index=current_index)


def get_elastic_client(esd_url, tlsauth_key, tlsauth_cert):
    """create esclient"""

    esclient_options = {}
    if tlsauth_key and tlsauth_cert:
        ctx = ssl.create_default_context()
        ctx.load_cert_chain(tlsauth_cert, tlsauth_key)
        # either fix tls version or use post auth handshake
        # ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.post_handshake_auth = True
        esclient_options['ssl_context'] = ctx

    return Elasticsearch([esd_url], **esclient_options)


def sync_vulnsearch(cvesearch_url, esd_url, namelen, tlsauth_key, tlsauth_cert):
    """
    synchronize vulnsearch esd index with cvesearch data for all cpe notes in storage
    """

    esclient = get_elastic_client(esd_url, tlsauth_key, tlsauth_cert)
    indexer = BulkIndexer(esclient)
    alias = 'vulnsearch'
    index = f'{alias}-{datetime.now().strftime("%Y%m%d%H%M%S")}'

    for note in windowed_query(Note.query.filter(Note.xtype == 'cpe'), Note.id):
        for icpe in json.loads(note.data):
            try:
                parsed_cpe = CPE(icpe)
            except Exception:  # pylint: disable=broad-except  ; library does not provide own core exception class
                current_app.logger.warning(f'invalid cpe, note_id:{note.id} {icpe}')
                continue

            if not parsed_cpe.get_version()[0]:
                continue

            for cve in cvefor(icpe, cvesearch_url, tlsauth_key, tlsauth_cert):
                data_id, data = vulndata(note, parsed_cpe, cve, namelen)
                indexer.index(index, data_id, data)

    indexer.flush()
    update_managed_indices(esclient, index, alias)
    # print cache stats
    current_app.logger.debug(f'cvefor cache: {cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect
