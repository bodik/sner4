# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage version info map functions
"""

import json
import re
from dataclasses import asdict, dataclass, field
from hashlib import md5

from cpe import CPE
from flask import current_app
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sner.lib import get_nested_key
from sner.server.extensions import db
from sner.server.storage.models import Host, Note, Service, Versioninfo


def versioninfo_docid(host_id, host_address, host_hostname, service_proto, service_port, via_target, product):  # pylint: disable=too-many-arguments
    """compute versioninfo docid"""

    keydata = '|'.join(map(str, [
        host_id,
        host_address,
        host_hostname,
        service_proto,
        service_port,
        via_target,
        product,
    ]))
    return md5(keydata.encode()).hexdigest()


@dataclass
class ExtractedVersion:
    """extracted version"""
    product: str
    version: str


@dataclass
class VMapItem:
    """raw map item"""
    # pylint: disable=too-many-instance-attributes

    host_id: int
    host_address: str
    host_hostname: str
    service_proto: str
    service_port: int
    via_target: str
    product: str
    version: str
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.product = self.product.lower()

    def aggkey(self):
        """compute vmap aggregation key"""

        return versioninfo_docid(
            self.host_id,
            self.host_address,
            self.host_hostname,
            self.service_proto,
            self.service_port,
            self.via_target,
            self.product
        )


class VMap:
    """raw version info map"""

    def __init__(self):
        self.data = {}

    def add(self, **kwargs):
        """add data into raw map, account for uniqueness and aggregation"""

        entry = VMapItem(**kwargs)
        aggkey = entry.aggkey()

        if aggkey in self.data:
            self.data[aggkey].version = entry.version
            self.data[aggkey].extra.update(entry.extra)
        else:
            self.data[aggkey] = entry

    def flush(self):
        """upsert database, prune gone"""

        current_app.logger.debug('upsert versioninfo %d items', len(self.data))
        for key, val in self.data.items():
            db.session.execute(
                pg_insert(Versioninfo)
                .values({'id': key, **val.__dict__})
                .on_conflict_do_update(constraint='versioninfo_pkey', set_=val.__dict__)
            )
        db.session.commit()

        affected_rows = Versioninfo.query.filter(Versioninfo.id.not_in(self.data.keys())).delete(synchronize_session=False)
        current_app.logger.debug('prune versioninfo %d items', affected_rows)
        db.session.commit()
        db.session.expire_all()

    def __len__(self):
        """return data dict size"""

        return len(self.data)


class VersioninfoManager:
    """version info map manager"""

    @staticmethod
    def _base_note_query():
        return (
            db.session.query().select_from(Note)
            .outerjoin(Host, Note.host_id == Host.id)
            .outerjoin(Service, Note.service_id == Service.id)
            .add_columns(
                Host.id.label('host_id'),
                Host.address.label('host_address'),
                Host.hostname.label('host_hostname'),
                Service.proto.label('service_proto'),
                Service.port.label('service_port'),
                Note.via_target,
                Note.data
            )
        )

    @staticmethod
    def _jsondata_iterator(query):
        """note.data json decode iterator"""

        for sourcedata in query.all():
            item = sourcedata._asdict()
            try:
                data = json.loads(item.pop('data'))
            except json.decoder.JSONDecodeError:
                current_app.logger.warning('note.data invalid json, %s', sourcedata._asdict())
                continue
            yield item, data

    @staticmethod
    def extract_version(value):
        """extract product,version tuple from string"""

        if match := re.match(r'(?P<product>[^\d]+)[/ \-]v?(?P<version>\d+(?:\.[-_a-zA-Z\d]+)*)', value):
            return ExtractedVersion(match.group('product'), match.group('version'))

        if match := re.match(r'(?P<product>[^\d]+) ver:(?P<version>\d+(?:\.[-_a-zA-Z\d]+)*)', value):
            return ExtractedVersion(match.group('product'), match.group('version'))

        return None

    @classmethod
    def rebuild(cls):
        """rebuild versioninfo map"""

        vmap = VMap()
        vmap = cls.collect_cpes(vmap)
        vmap = cls.collect_nmap_bannerdict(vmap)
        vmap = cls.collect_nmap_httpgenerator(vmap)
        vmap = cls.collect_nmap_mysqlinfo(vmap)
        vmap = cls.collect_nmap_rdpntlminfo(vmap)
        vmap.flush()

    @classmethod
    def collect_nmap_bannerdict(cls, vmap):
        """collects nmap.banner_dict notes"""

        query = cls._base_note_query().filter(Note.xtype == 'nmap.banner_dict')
        for item, data in cls._jsondata_iterator(query):
            item_extracted = False

            # {
            #   "product": "Apache httpd",
            #   "version": "2.4.6", ...
            # }
            if 'product' in data:
                tmp = (
                    {'version': data['version']}
                    if 'version' in data
                    else {'version': '0', 'extra': {'flag': 'noversion'}}
                )
                vmap.add(**item, product=data["product"], **tmp)
                item_extracted = True

            # {
            #   "product": "Apache httpd",
            #   "version": "2.2.21",
            #   "extrainfo": "(Win32) mod_ssl/2.2.21 OpenSSL/1.0.0e PHP/5.3.8 mod_perl/2.0.4 Perl/v5.10.1"
            # }
            if {'product', 'extrainfo'}.issubset(data.keys()) and data["product"] == "Apache httpd":
                extra = {}
                for part in data["extrainfo"].split(' '):
                    if match := re.match(r'\((?P<osflavor>.*)\)', part):
                        extra["os"] = match.group('osflavor').lower()
                    if extracted := cls.extract_version(part):
                        vmap.add(**item, **asdict(extracted), extra=extra)
                        item_extracted = True

            if not item_extracted:
                current_app.logger.debug(f'{__name__} skipped {item} {data}')

        return vmap

    @classmethod
    def collect_nmap_httpgenerator(cls, vmap):
        """collects nmap.http_generator notes"""

        query = cls._base_note_query().filter(Note.xtype == 'nmap.http-generator')
        for item, data in cls._jsondata_iterator(query):
            item_extracted = False

            if extracted := cls.extract_version(data.get('output', '')):
                vmap.add(**item, **asdict(extracted))
                item_extracted = True

            if not item_extracted:
                current_app.logger.debug(f'{__name__} skipped {item} {data}')

        return vmap

    @classmethod
    def collect_nmap_mysqlinfo(cls, vmap):
        """collects nmap.mysql-info notes"""

        version_regexp = r'(?:.*?)-(?P<version>.*?)-(?P<product>.*?)-(?P<flavor>.*)'

        query = cls._base_note_query().filter(Note.xtype == 'nmap.mysql-info')
        for item, data in cls._jsondata_iterator(query):
            if verdata := get_nested_key(data, 'elements', 'Version'):
                if match := re.match(version_regexp, verdata):
                    vmap.add(
                        **item,
                        product=match.group('product'),
                        version=match.group('version'),
                        extra={'full_version': verdata}
                    )

        return vmap

    @classmethod
    def collect_nmap_rdpntlminfo(cls, vmap):
        """collects nmap.rdp-ntlm-info notes"""

        query = cls._base_note_query().filter(Note.xtype == 'nmap.rdp-ntlm-info')
        for item, data in cls._jsondata_iterator(query):
            if verdata := get_nested_key(data, 'elements', 'Product_Version'):
                vmap.add(**item, product="Microsoft Windows", version=verdata)

        return vmap

    @classmethod
    def collect_cpes(cls, vmap):
        """collects cpe notes"""

        def cpe_iterator(cpes):
            for icpe in cpes:
                try:
                    parsed_cpe = CPE(icpe)
                except Exception:  # pylint: disable=broad-except  ; library does not provide own core exception class
                    current_app.logger.warning(f'invalid cpe, {icpe}')
                    continue
                product = ' '.join(filter(None, [parsed_cpe.get_vendor()[0], parsed_cpe.get_product()[0]]))
                version = parsed_cpe.get_version()[0]
                if product and version:
                    yield ExtractedVersion(product, version)

        query = cls._base_note_query().filter(Note.xtype == 'cpe')
        for item, data in cls._jsondata_iterator(query):
            for extracted in cpe_iterator(data):
                vmap.add(**item, **asdict(extracted))

        return vmap
