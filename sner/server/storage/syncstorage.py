# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage sync_storage core impl
"""

from hashlib import md5
from time import time

from sner.server.api.schema import PublicHostSchema
from sner.server.utils import windowed_query
from sner.server.storage.models import Host
from sner.server.storage.vulnsearch import BulkIndexer, get_elastic_client, update_managed_indices


ES_ALIAS = 'storage_host'


def sync_storage(esd_url, tlsauth_key, tlsauth_cert):
    """
    sychronize storage do esd
    """

    esclient = get_elastic_client(esd_url, tlsauth_key, tlsauth_cert)
    indexer = BulkIndexer(esclient)
    current_index = f'{ES_ALIAS}-{time()}'
    schema = PublicHostSchema()

    for host in windowed_query(Host.query, Host.id):
        data_id = md5(f'{host.address}'.encode()).hexdigest()
        # host.notes relation holds all notes regardless of it's link to service filter response model ...
        host_data = {
            **host.__dict__,
            'services': host.services,
            'notes': [note for note in host.notes if note.service_id is None]
        }
        indexer.index(current_index, data_id, schema.dump(host_data))

    indexer.flush()
    update_managed_indices(esclient, current_index, ES_ALIAS)
