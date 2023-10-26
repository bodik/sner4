# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage elastic client
"""

import functools
import ssl
import warnings

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ElasticsearchWarning
from elasticsearch.helpers import bulk as es_bulk


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


class BulkIndexer:
    """elasticsearch bulk indexing buffer"""

    TIMEOUT = 30

    def __init__(self, esd_url, tlsauth_key, tlsauth_cert, buflen=1000):
        """constructor"""

        self.buf = []
        self.buflen = buflen

        esclient_options = {}
        if tlsauth_key and tlsauth_cert:
            ctx = ssl.create_default_context()
            ctx.load_cert_chain(tlsauth_cert, tlsauth_key)
            # either fix tls version or use post auth handshake
            # ctx.maximum_version = ssl.TLSVersion.TLSv1_2
            ctx.post_handshake_auth = True
            esclient_options['ssl_context'] = ctx
        self.esclient = Elasticsearch([esd_url], request_timeout=self.TIMEOUT, **esclient_options)

    def initialize(self, index):  # pragma: nocover  ; mocked
        """initialize empty index"""

        if not self.esclient.indices.exists(index=index):
            self.esclient.indices.create(index=index)

    def index(self, index, doc_id, doc):
        """index item in buffered way"""

        self.buf.append({'_index': index, '_id': doc_id, '_source': doc})
        if len(self.buf) > self.buflen:
            return self.flush()
        return ()

    @ignore_warning(ElasticsearchWarning)
    def flush(self):
        """flush buffer"""

        res = es_bulk(self.esclient, self.buf, request_timeout=self.TIMEOUT)
        self.buf = []
        return res

    @ignore_warning(ElasticsearchWarning)
    def update_alias(self, alias, current_index):  # pragma: nocover  ; mocked
        """update alias, pune old indices"""

        if not self.esclient.indices.exists(index=current_index):
            return

        if self.esclient.indices.exists(index=current_index):
            self.esclient.indices.put_alias(index=current_index, name=alias)
            self.esclient.indices.refresh(index=current_index)

        for item in self.esclient.indices.get(index=f'{alias}-*'):
            if item != current_index:
                self.esclient.indices.delete(index=item)
