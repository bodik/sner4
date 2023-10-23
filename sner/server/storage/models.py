# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sqlalchemy models

## Note on Vuln/Note via_target attribute

The core of storage data structure are models Host and Service, which
represents IP-centric view on the monitored network -- core informations for
the IP/TCP/UDP discovery and scanning.

Than there's a World-Wide-Web, where name-based virtualhosting might apply and
it's usage yields in an unusual situations in tools used to scan. Namely
HTTP/WEB scanning modules of Nmap and Nessus yields different results with
different target specifications such as hostname1, hostname2, ipaddress, but
under same set of identifiers (module name, vulnerability name). Eg. when
scanning 'appa' and 'appb' servers hosted at single 'address', there might be
two vulnerabilities names 'SQL Injection' with same 'Nessus NASL ID' on the
same target IP address, but having different content.

During import (and in continuous network monitoring), we'd like to keep
IP-centric base of Host model so in simple case, some data might get
overwritten when upsert of vulnerability takes account Host.address, service
and vuln.name.

To solve the issue, Note and Vuln has additional model attribute 'via_target',
which is also taken into account during storage upserts, and parsers should
fill in the best value as possible in order to prevent accidental data
overwrite and support upsert/update mechanism used during continuous network
monitoring.
"""
# pylint: disable=too-few-public-methods,abstract-method

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from sner.lib import format_host_address
from sner.server.extensions import db
from sner.server.materialized_views import create_materialized_view
from sner.server.models import SelectableEnum


class StorageModelBase(db.Model):
    """storage model base"""

    __abstract__ = True

    def update(self, obj):
        """Update model from data object. Existing values are not overwriten with empty values."""

        iterator = obj.__dict__ if hasattr(obj, '__dict__') else obj
        for key, value in iterator.items():
            if value and hasattr(self, key):
                setattr(self, key, value)


class Host(StorageModelBase):
    """basic host (ip-centric) model"""

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(postgresql.INET, nullable=False)
    hostname = db.Column(db.String(256))
    os = db.Column(db.Text)
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rescan_time = db.Column(db.DateTime, default=datetime.utcnow)

    services = relationship('Service', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)
    vulns = relationship('Vuln', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)
    notes = relationship('Note', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)

    def __repr__(self):
        return f'<Host {self.id}: {self.address} {self.hostname}>'


class Service(StorageModelBase):
    """discovered host service"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('host.id', ondelete='CASCADE'), nullable=False)
    proto = db.Column(db.String(250), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String(250))
    name = db.Column(db.String(250))
    info = db.Column(db.Text)
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rescan_time = db.Column(db.DateTime, default=datetime.utcnow)
    import_time = db.Column(db.DateTime)

    host = relationship('Host', back_populates='services')
    vulns = relationship('Vuln', back_populates='service', cascade='delete,delete-orphan', passive_deletes=True)
    notes = relationship('Note', back_populates='service', cascade='delete,delete-orphan', passive_deletes=True)

    def __repr__(self):
        host = format_host_address(self.host.address) if self.host else None
        return f'<Service {self.id}: {host} {self.proto}.{self.port}>'


class SeverityEnum(SelectableEnum):
    """severity enum"""

    UNKNOWN = 'unknown'
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class Vuln(StorageModelBase):
    """vulnerability model; heavily inspired by metasploit; hdm rulez"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('host.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'))
    via_target = db.Column(db.String(250))
    name = db.Column(db.String(1000), nullable=False)
    xtype = db.Column(db.String(250))
    severity = db.Column(db.Enum(SeverityEnum, values_callable=lambda x: [member.value for member in SeverityEnum]), nullable=False)
    descr = db.Column(db.Text)
    data = db.Column(db.Text)
    refs = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rescan_time = db.Column(db.DateTime, default=datetime.utcnow)
    import_time = db.Column(db.DateTime)

    host = relationship('Host', back_populates='vulns')
    service = relationship('Service', back_populates='vulns')

    def __repr__(self):
        host = format_host_address(self.host.address) if self.host else None
        service = f'{self.service.proto}.{self.service.port}' if self.service else None
        return f'<Vuln {self.id}: {host} {service} {self.xtype}>'


class Note(StorageModelBase):
    """host assigned note, generic data container"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('host.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'))
    via_target = db.Column(db.String(250))
    xtype = db.Column(db.String(250))
    data = db.Column(db.Text)
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    import_time = db.Column(db.DateTime)

    host = relationship('Host', back_populates='notes')
    service = relationship('Service', back_populates='notes')

    def __repr__(self):
        host = format_host_address(self.host.address) if self.host else None
        service = f'{self.service.proto}.{self.service.port}' if self.service else None
        return f'<Note {self.id}: {host} {service} {self.xtype}>'


class VersionInfoTemp(StorageModelBase):
    """version info model, temporary table"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, nullable=False)
    host_address = db.Column(postgresql.INET, nullable=False)
    host_hostname = db.Column(db.String(256))
    service_proto = db.Column(db.String(250))
    service_port = db.Column(db.Integer)
    via_target = db.Column(db.String(250))

    product = db.Column(db.String(250))
    version = db.Column(db.String(250))
    extra = db.Column(db.JSON)


class VersionInfo(StorageModelBase):
    """version info (materialized view) model"""

    __table__ = create_materialized_view('version_info', select(VersionInfoTemp), db.metadata)


class VulnsearchTemp(StorageModelBase):
    """local vulnsearch model, temporary table"""

    id = db.Column(db.String(32), primary_key=True)
    host_id = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer)
    host_address = db.Column(postgresql.INET, nullable=False)
    host_hostname = db.Column(db.String(256))
    service_proto = db.Column(db.String(250))
    service_port = db.Column(db.Integer)
    via_target = db.Column(db.String(250))

    cveid = db.Column(db.String(250))
    name = db.Column(db.Text)
    description = db.Column(db.Text)
    cvss = db.Column(db.Float)
    cvss3 = db.Column(db.Float)
    attack_vector = db.Column(db.String(250))
    data = db.Column(db.JSON)
    cpe = db.Column(db.JSON)


class Vulnsearch(StorageModelBase):
    """version info (materialized view) model"""

    __table__ = create_materialized_view('vulnsearch', select(VulnsearchTemp), db.metadata)
