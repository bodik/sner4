# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage elastic storage core impl
"""

from datetime import datetime
from hashlib import md5

from flask import current_app
from marshmallow import fields

from sner.server.api.schema import PublicHostSchema, PublicNoteSchema, PublicServiceSchema
from sner.server.utils import windowed_query
from sner.server.storage.elastic import BulkIndexer
from sner.server.storage.models import Host, Note, Service


class ElasticHostSchema(PublicHostSchema):
    """elastic storage_host schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()
    services_count = fields.Integer()
    vulns_count = fields.Integer()
    notes_count = fields.Integer()


class ElasticServiceSchema(PublicServiceSchema):
    """elastic storage_service schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()


class ElasticNoteSchema(PublicNoteSchema):
    """elastic storage_note schema"""

    host_address = fields.String(required=True)
    host_hostname = fields.String()
    service_proto = fields.String()
    service_port = fields.Integer()


class ElasticStorageManager():
    """elastic storage manager"""

    def __init__(self, esd_url, tlsauth_key=None, tlsauth_cert=None):
        self.esd_url = esd_url
        self.tlsauth_key = tlsauth_key
        self.tlsauth_cert = tlsauth_cert
        self.rebuild_buflen = current_app.config['SNER_ELASTICSTORAGE_REBUILD_BUFLEN']

    def rebuild(self):
        """sychronize storage do elastic"""

        index_time = datetime.now().strftime('%Y%m%d%H%M%S')
        indexer = BulkIndexer(self.esd_url, self.tlsauth_key, self.tlsauth_cert, self.rebuild_buflen)
        self.rebuild_hosts(indexer, index_time)
        self.rebuild_services(indexer, index_time)
        self.rebuild_notes(indexer, index_time)

    def rebuild_hosts(self, indexer, index_time):
        """sync hosts to elastic"""

        alias = 'storage_host'
        index = f'{alias}-{index_time}'
        schema = ElasticHostSchema()
        query = Host.query

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

    def rebuild_services(self, indexer, index_time):
        """sync services to elastic"""

        alias = 'storage_service'
        index = f'{alias}-{index_time}'
        schema = ElasticServiceSchema()
        query = Service.query.outerjoin(Host)

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

    def rebuild_notes(self, indexer, index_time):
        """sync notes to elastic"""

        alias = 'storage_note'
        index = f'{alias}-{index_time}'
        schema = ElasticNoteSchema()
        query = Note.query.outerjoin(Host, Note.host_id == Host.id).outerjoin(Service, Note.service_id == Service.id)

        for note in windowed_query(query, Note.id):
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
