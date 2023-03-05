# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sqlalchemy models
"""
# pylint: disable=too-few-public-methods,abstract-method

import os
from datetime import datetime

from flask import current_app
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, PrimaryKeyConstraint

from sner.server.extensions import db


class Queue(db.Model):
    """task configuration for queue of targets"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False, unique=True)
    config = db.Column(db.Text)
    group_size = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    reqs = db.Column(postgresql.ARRAY(db.String, dimensions=1), nullable=False, default=list)

    targets = relationship('Target', back_populates='queue', cascade='delete,delete-orphan', passive_deletes=True)
    jobs = relationship('Job', back_populates='queue', cascade='delete,delete-orphan', passive_deletes=True)

    def __repr__(self):
        return f'<Queue {self.id}: {self.name}>'

    @property
    def data_abspath(self):
        """return absolute path of the queue data directory"""
        return os.path.join(current_app.config['SNER_VAR'], 'scheduler', f'queue-{self.id}') if self.id else None


class Target(db.Model):
    """single target in queue"""

    id = db.Column(db.Integer, primary_key=True)
    queue_id = db.Column(db.Integer, db.ForeignKey('queue.id', ondelete='CASCADE'), nullable=False)
    target = db.Column(db.Text, nullable=False)
    hashval = db.Column(db.Text, nullable=False)

    queue = relationship('Queue', back_populates='targets')

    __table_args__ = (
        Index('target_queueid_hashval', 'queue_id', 'hashval'),  # get_assignment: select random target from queue
        Index('target_hashval', 'hashval')  # job_done: enable readynet on all queues
    )

    def __repr__(self):
        return f'<Target {self.id}: {self.target}>'


class Heatmap(db.Model):
    """rate-limit heatmap item"""

    hashval = db.Column(db.String, nullable=False)
    count = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('hashval', name='heatmap_pkey'),
    )

    def __repr__(self):
        return f'<Heatmap {self.hashval}: {self.count}>'


class Readynet(db.Model):
    """represents list of networks available for job assignment"""

    queue_id = db.Column(db.Integer, db.ForeignKey('queue.id', ondelete='CASCADE'), nullable=False)
    hashval = db.Column(db.String, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('queue_id', 'hashval', name='readynet_pkey'),  # enqueue: ensure uniqueness
        Index('readynet_hashval', 'hashval')  # get_assignment: remove readynet when hot
    )

    def __repr__(self):
        return f'<Readynet {self.queue_id} {self.hashval}>'


class Job(db.Model):
    """assigned job"""

    id = db.Column(db.String(36), primary_key=True)
    queue_id = db.Column(db.Integer, db.ForeignKey('queue.id', ondelete='CASCADE'))
    assignment = db.Column(db.Text, nullable=False)
    retval = db.Column(db.Integer)
    time_start = db.Column(db.DateTime, default=datetime.utcnow)
    time_end = db.Column(db.DateTime)

    queue = relationship('Queue', back_populates='jobs')

    def __repr__(self):
        return f'<Job {self.id}>'

    @property
    def output_abspath(self):
        """return absolute path to the output data file acording to current app config"""
        return os.path.join(self.queue.data_abspath, self.id)
