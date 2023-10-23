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
from sqlalchemy.dialects.postgresql import ARRAY, CIDR, insert as pg_insert

from sner.server.extensions import db
from sner.server.storage.elastic import BulkIndexer
from sner.server.storage.models import Host, Note, VulnsearchTemp
from sner.server.materialized_views import refresh_materialized_view
from sner.server.utils import windowed_query


def get_attack_vector(cve):
    """get access vector from cve; handle different available data with grace"""

    # cvss3
    if 'exploitability3' in cve:
        return cve['exploitability3']['attackvector']

    # cvss
    if 'access' in cve:
        return cve['access']['vector']

    return None


def cpe_notes(host_filter=None):
    """storage data cpe notes iterator"""

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


def vulndata_docid(host_address, service_proto, service_port, cveid):
    """vulnsearch id generation helper"""

    return md5(f'{host_address}|{service_proto}|{service_port}|{cveid}'.encode()).hexdigest()


def vulndata(note, parsed_cpe, cve, namelen):
    """project vulndata object"""

    data_id = vulndata_docid(
        note.host.address,
        note.service.proto if note.service else None,
        note.service.port if note.service else None,
        cve["id"]
    )

    data = {
        'host_id': note.host_id,
        'service_id': note.service_id,
        'host_address': note.host.address,
        'host_hostname': note.host.hostname,
        'service_proto': note.service.proto if note.service else None,
        'service_port': note.service.port if note.service else None,
        'via_target': note.via_target,

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


class LocaldbWriter:
    """bulk inserting buffer"""

    def __init__(self, buflen=1000):
        """constructor"""

        self.buf = []
        self.buflen = buflen

    def initialize(self):
        """cleanup build tables"""

        VulnsearchTemp.query.delete()
        db.session.commit()

    def index(self, doc_id, doc):
        """index item in buffered way"""

        doc['cpe_full'] = doc['cpe']['full']
        self.buf.append({'id': doc_id, **doc})
        if len(self.buf) > self.buflen:
            self.flush()

    def flush(self):
        """flush buffer"""

        if self.buf:
            db.session.connection().execute(pg_insert(VulnsearchTemp), self.buf)
            db.session.commit()
            self.buf = []

    def refresh_view(self):
        """refresh view"""

        refresh_materialized_view(db.session, 'vulnsearch')
        db.session.commit()


class VulnsearchManager:
    """vulnsearch manager"""

    def __init__(self, cvesearch_url, tlsauth_key=None, tlsauth_cert=None):
        self.cvesearch_url = cvesearch_url
        self.tlsauth_key = tlsauth_key
        self.tlsauth_cert = tlsauth_cert
        self.namelen = current_app.config['SNER_VULNSEARCH_NAMELEN']
        self.rebuild_buflen = current_app.config['SNER_VULNSEARCH_REBUILD_BUFLEN']

    @functools.lru_cache(maxsize=256)
    def cvefor(self, cpe):  # pragma: nocover  ; mocked
        """query cvesearch and filter out response"""

        res = requests.get(f'{self.cvesearch_url}/api/cvefor/{cpe}', cert=(self.tlsauth_cert, self.tlsauth_key))
        if res.status_code == HTTPStatus.OK:
            # filter unused/oversized data; ex. linux:linux_kernel:xyz is about 800MB
            data = res.json()
            res = None  # free memory
            for cve in data:
                for field in ['vulnerable_configuration', 'vulnerable_configuration_cpe_2_2', 'vulnerable_product']:
                    cve.pop(field, None)
            return data

        if res.status_code == HTTPStatus.NOT_FOUND:
            return []

        current_app.logger.warning('cvesearch call failed')
        return []

    def rebuild_elastic(self, esd_url, host_filter=None):
        """
        synchronize vulnsearch esd index with cvesearch data for all cpe notes in storage
        """

        alias = 'vulnsearch'
        index = f'{alias}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        esd_indexer = (
            BulkIndexer(esd_url, self.tlsauth_key, self.tlsauth_cert, self.rebuild_buflen)
            if esd_url
            else None
        )

        for note, icpe, parsed_cpe in cpe_notes(host_filter):
            for cve in self.cvefor(icpe):
                data_id, data = vulndata(note, parsed_cpe, cve, self.namelen)
                esd_indexer.index(index, data_id, data)

        esd_indexer.flush()
        esd_indexer.update_alias(alias, index)
        current_app.logger.debug(f'cvefor cache: {self.cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect

    def rebuild_localdb(self):
        """build local vulnsearch tables"""

        vulnsearch_writer = LocaldbWriter(self.rebuild_buflen)
        vulnsearch_writer.initialize()

        for note, icpe, parsed_cpe in cpe_notes():
            for cve in self.cvefor(icpe):
                data_id, data = vulndata(note, parsed_cpe, cve, self.namelen)
                vulnsearch_writer.index(data_id, data)

        vulnsearch_writer.flush()
        vulnsearch_writer.refresh_view()
        current_app.logger.debug(f'cvefor cache: {self.cvefor.cache_info()}')  # pylint: disable=no-value-for-parameter  ; lru decorator side-effect
