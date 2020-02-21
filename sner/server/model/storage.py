# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sqlalchemy models
"""
# pylint: disable=too-few-public-methods,abstract-method

from datetime import datetime

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from sner.server import db
from sner.server.model import SelectableEnum


class Host(db.Model):
    """basic host (ip-centric) model"""

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(postgresql.INET, nullable=False)
    hostname = db.Column(db.String(256))
    os = db.Column(db.Text)
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    services = relationship('Service', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)
    vulns = relationship('Vuln', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)
    notes = relationship('Note', back_populates='host', cascade='delete,delete-orphan', passive_deletes=True)

    def __repr__(self):
        return '<Host %s: %s (%s)>' % (self.id, self.address, self.hostname if self.hostname else '')


class Service(db.Model):
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

    host = relationship('Host', back_populates='services')
    vulns = relationship('Vuln', back_populates='service', cascade='delete,delete-orphan', passive_deletes=True)
    notes = relationship('Note', back_populates='service', cascade='delete,delete-orphan', passive_deletes=True)

    def __repr__(self):
        return '<Service %s: %s.%d>' % (self.id, self.proto, self.port)


class SeverityEnum(SelectableEnum):
    """severity enum"""

    unknown = 'unknown'
    info = 'info'
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'


class Vuln(db.Model):
    """vulnerability model; heavily inspired by metasploit; hdm rulez"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('host.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'))
    name = db.Column(db.String(1000), nullable=False)
    xtype = db.Column(db.String(250))
    severity = db.Column(db.Enum(SeverityEnum), nullable=False)
    descr = db.Column(db.Text)
    data = db.Column(db.Text)
    refs = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)

    host = relationship('Host', back_populates='vulns')
    service = relationship('Service', back_populates='vulns')

    def __repr__(self):
        return '<Vuln %s: %s>' % (self.id, self.xtype)


class Note(db.Model):
    """host assigned note, generic data container"""

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('host.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'))
    xtype = db.Column(db.String(250))
    data = db.Column(db.Text)
    tags = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=[])
    comment = db.Column(db.Text)

    host = relationship('Host', back_populates='notes')
    service = relationship('Service', back_populates='notes')

    def __repr__(self):
        return '<Note %s: %s>' % (self.id, self.xtype)
