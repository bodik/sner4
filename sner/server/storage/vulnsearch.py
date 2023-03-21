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
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY, CIDR

from sner.server.storage.elastic import BulkIndexer
from sner.server.storage.models import Host, Note
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


def get_attack_vector(cve):
    """get access vector from cve; handle different available data with grace"""

    # cvss3
    if 'exploitability3' in cve:
        return cve['exploitability3']['attackvector']

    # cvss
    if 'access' in cve:
        return cve['access']['vector']

    return None


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
        'attack_vector': get_attack_vector(cve),
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


def cpe_notes(host_filter=None):
    """cpe notes iterator"""

    query = Note.query.filter(Note.xtype == 'cpe').outerjoin(Host)
    if host_filter:
        host_filter_expr = Host.address.op('<<=')(func.any(func.cast(host_filter, ARRAY(CIDR)))) if host_filter else None
        query = query.filter(host_filter_expr)

    for note in windowed_query(query, Note.id):
        for icpe in json.loads(note.data):
            try:
                parsed_cpe = CPE(icpe)
            except Exception:  # pylint: disable=broad-except  ; library does not provide own core exception class
                current_app.logger.warning(f'invalid cpe, note_id:{note.id} {icpe}')
                continue

            if not parsed_cpe.get_version()[0]:
                continue

            yield note, icpe, parsed_cpe


def sync_vulnsearch(cvesearch_url, esd_url, namelen, tlsauth_key=None, tlsauth_cert=None, host_filter=None):  # noqa: E501  pylint: disable=too-many-arguments
    """
    synchronize vulnsearch esd index with cvesearch data for all cpe notes in storage
    """

    indexer = BulkIndexer(esd_url, tlsauth_key, tlsauth_cert, buflen=current_app.config['SNER_SYNCVULNSEARCH_ELASTIC_BUFLEN'])
    alias = 'vulnsearch'
    index = f'{alias}-{datetime.now().strftime("%Y%m%d%H%M%S")}'

    for note, icpe, parsed_cpe in cpe_notes(host_filter):
        for cve in cvefor(icpe, cvesearch_url, tlsauth_key, tlsauth_cert):
            data_id, data = vulndata(note, parsed_cpe, cve, namelen)
            indexer.index(index, data_id, data)

    indexer.flush()
    indexer.update_alias(alias, index)
    # print cache stats
    current_app.logger.debug(f'cvefor cache: {cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect
