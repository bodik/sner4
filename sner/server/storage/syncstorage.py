# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage sync_storage core impl
"""

from hashlib import md5
from time import time

from sner.server.api.schema import ElasticNoteSchema, ElasticServiceSchema, PublicHostSchema
from sner.server.utils import windowed_query
from sner.server.storage.models import Host, Note, Service
from sner.server.storage.vulnsearch import BulkIndexer, get_elastic_client, update_managed_indices


def sync_storage(esd_url, tlsauth_key, tlsauth_cert):
    """
    sychronize storage do esd
    """

    esclient = get_elastic_client(esd_url, tlsauth_key, tlsauth_cert)
    indexer = BulkIndexer(esclient)

    # storage_host
    alias = 'storage_host'
    current_index = f'{alias}-{time()}'
    schema = PublicHostSchema()

    for host in windowed_query(Host.query, Host.id):
        data_id = md5(f'{host.address}'.encode()).hexdigest()
        # host.notes relation holds all notes regardless of it's link to service filter response model ...
        data = {
            **host.__dict__,
            'services': host.services,
            'notes': [note for note in host.notes if note.service_id is None]
        }
        indexer.index(current_index, data_id, schema.dump(data))

    indexer.flush()
    update_managed_indices(esclient, current_index, alias)

    # storage_service
    alias = 'storage_service'
    current_index = f'{alias}-{time()}'
    schema = ElasticServiceSchema()

    for service in windowed_query(Service.query, Service.id):
        data_id = md5(f'{service.host.address}|{service.proto}|{service.port}'.encode()).hexdigest()
        data = {
            'host_address': service.host.address,
            'host_hostname': service.host.hostname,
            **service.__dict__
        }
        indexer.index(current_index, data_id, schema.dump(data))

    indexer.flush()
    update_managed_indices(esclient, current_index, alias)

    # storage_note
    alias = 'storage_note'
    current_index = f'{alias}-{time()}'
    schema = ElasticNoteSchema()

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
        indexer.index(current_index, data_id, schema.dump(data))

    indexer.flush()
    update_managed_indices(esclient, current_index, alias)
