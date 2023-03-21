# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage sync_storage core impl
"""

from datetime import datetime
from hashlib import md5

from flask import current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY, CIDR

from sner.server.api.schema import ElasticHostSchema, ElasticNoteSchema, ElasticServiceSchema
from sner.server.utils import windowed_query
from sner.server.storage.elastic import BulkIndexer
from sner.server.storage.models import Host, Note, Service


def sync_hosts(indexer, index_time, host_filter_expr=None):
    """sync hosts to elastic"""

    alias = 'storage_host'
    index = f'{alias}-{index_time}'
    schema = ElasticHostSchema()
    query = Host.query
    if host_filter_expr is not None:
        query = query.filter(host_filter_expr)

    for host in windowed_query(query, Host.id):
        data_id = md5(f'{host.address}'.encode()).hexdigest()
        # host.notes relation holds all notes regardless of it's link to service filter response model ...
        data = {
            **host.__dict__,
            'services': host.services,
            'notes': [note for note in host.notes if note.service_id is None],
            'host_address': host.address,
            'host_hostname': host.hostname,
            'services_count': len(host.services),
            'vulns_count': len(host.vulns),
            'notes_count': len(host.notes)
        }
        indexer.index(index, data_id, schema.dump(data))

    indexer.flush()
    indexer.update_alias(alias, index)


def sync_services(indexer, index_time, host_filter_expr=None):
    """sync services to elastic"""

    alias = 'storage_service'
    index = f'{alias}-{index_time}'
    schema = ElasticServiceSchema()
    query = Service.query.outerjoin(Host)
    if host_filter_expr is not None:
        query = query.filter(host_filter_expr)

    for service in windowed_query(query, Service.id):
        data_id = md5(f'{service.host.address}|{service.proto}|{service.port}'.encode()).hexdigest()
        data = {
            'host_address': service.host.address,
            'host_hostname': service.host.hostname,
            **service.__dict__
        }
        indexer.index(index, data_id, schema.dump(data))

    indexer.flush()
    indexer.update_alias(alias, index)


def sync_notes(indexer, index_time, host_filter_expr=None):
    """sync notes to elastic"""

    alias = 'storage_note'
    index = f'{alias}-{index_time}'
    schema = ElasticNoteSchema()
    query = Note.query.outerjoin(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id)
    if host_filter_expr is not None:
        query = query.filter(host_filter_expr)

    for note in windowed_query(Note.query, Note.id):
        data_id = md5(
            f'{note.host.address}'
            f'|{note.service.proto if note.service else None}'
            f'|{note.service.port if note.service else None}'
            f'|{note.xtype}'
            f'|{note.data}'.encode()
        ).hexdigest()
        data = {
            'host_address': note.host.address,
            'host_hostname': note.host.hostname,
            'service_proto': note.service.proto if note.service else None,
            'service_port': note.service.port if note.service else None,
            **note.__dict__
        }
        indexer.index(index, data_id, schema.dump(data))

    indexer.flush()
    indexer.update_alias(alias, index)


def sync_storage(esd_url, tlsauth_key=None, tlsauth_cert=None, host_filter=None):
    """
    sychronize storage do esd
    """

    indexer = BulkIndexer(esd_url, tlsauth_key, tlsauth_cert, buflen=current_app.config['SNER_SYNCSTORAGE_ELASTIC_BUFLEN'])
    host_filter_expr = Host.address.op('<<=')(func.any(func.cast(host_filter, ARRAY(CIDR)))) if host_filter else None
    index_time = datetime.now().strftime('%Y%m%d%H%M%S')

    sync_hosts(indexer, index_time, host_filter_expr)
    sync_services(indexer, index_time, host_filter_expr)
    sync_notes(indexer, index_time, host_filter_expr)
