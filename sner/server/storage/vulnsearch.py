# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage vulnsearch core impl
"""

import functools
import json
from datetime import datetime
from hashlib import md5
from http import HTTPStatus

import requests
from cpe import CPE
from flask import current_app

from sner.server.storage.elastic import BulkIndexer
from sner.server.storage.models import Note
from sner.server.utils import windowed_query


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


def sync_vulnsearch(cvesearch_url, esd_url, namelen, tlsauth_key, tlsauth_cert):
    """
    synchronize vulnsearch esd index with cvesearch data for all cpe notes in storage
    """

    indexer = BulkIndexer(esd_url, tlsauth_key, tlsauth_cert)
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
    indexer.update_alias(alias, index)
    # print cache stats
    current_app.logger.debug(f'cvefor cache: {cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect
