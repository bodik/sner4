# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server db command module
"""

import json
import os
import shutil

import click
from flask import current_app
from flask.cli import with_appcontext

from sner.server.auth.models import User
from sner.server.extensions import db
from sner.server.scheduler.core import QueueManager
from sner.server.scheduler.models import Queue
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln
from sner.server.utils import yaml_dump


def db_remove():
    """remove database artefacts (including var content)"""

    db.session.close()
    db.drop_all()
    db.session.execute('DROP TABLE IF EXISTS alembic_version')
    db.session.commit()

    path = current_app.config['SNER_VAR']
    for file_object in os.listdir(path):
        file_object_path = os.path.join(path, file_object)
        if os.path.isdir(file_object_path):
            shutil.rmtree(file_object_path)
        else:
            os.unlink(file_object_path)


def initdata_sner():
    """initialize sner queues"""

    db.session.add(Queue(
        name='sner six_dns_discover',
        config=yaml_dump({'module': 'six_dns_discover', 'delay': 1}),
        group_size=1000,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner six_enum_discover',
        config=yaml_dump({'module': 'six_enum_discover', 'rate': 100}),
        group_size=5,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner nmap servicedisco',
        config=yaml_dump({'module': 'nmap', 'args': '-sS --top-ports 10000 -Pn --scanflags ECESYN', 'timing_perhost': 2}),
        group_size=1000,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner nmap serviceversion',
        config=yaml_dump({'module': 'manymap', 'args': '-sV --version-intensity 4 -Pn', 'delay': 1}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner nmap script',
        config=yaml_dump({
            'module': 'manymap',
            'args': '-sS --script default,http-headers,ldap-rootdse,ssl-enum-ciphers,ssh-auth-methods --script-timeout 10m -Pn',
            'delay': 5
        }),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner jarm',
        config=yaml_dump({'module': 'jarm', 'delay': 1}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner testssl',
        config=yaml_dump({'module': 'testssl', 'delay': 1}),
        group_size=10,
        priority=15,
    ))


def initdata_pentest():
    """initialize pentest data"""

    db.session.add(Queue(
        name='pentest nmap fullsynscan',
        config=yaml_dump({
            'module': 'nmap',
            'args': '-sS -A -p1-65535 -Pn  --max-retries 3 --script-timeout 10m --min-hostgroup 20 --min-rate 900 --max-rate 1500'
        }),
        group_size=20,
        priority=10,
    ))


def initdata_dev():
    """initialize development data"""

    queue = Queue(
        name='dev dummy',
        config=yaml_dump({'module': 'dummy', 'args': '--dummyparam 1'}),
        group_size=2,
        priority=10,
        active=True
    )
    db.session.add(queue)
    db.session.commit()  # required to obtain queue.id
    QueueManager.enqueue(queue, ['1', '2', '3'])

    # storage test data host1
    aggregable_vuln = {
        'name': 'aggregable vuln',
        'xtype': 'x.agg',
        'severity': SeverityEnum.MEDIUM,
        'descr': 'aggregable vuln description',
        'data': 'agg vuln data',
        'tags': ['reportdata']
    }

    host = Host(
        address='127.4.4.4',
        hostname='testhost.testdomain.test<script>alert(1);</script>',
        os='Test Linux 1',
        comment='a some unknown service server'
    )
    db.session.add(host)

    service = Service(
        host=host,
        proto='tcp',
        port=12345,
        state='open:testreason',
        name='svcx',
        info='testservice banner',
        comment='manual testservice comment'
    )
    db.session.add(service)

    db.session.add(Vuln(host=host, **aggregable_vuln))

    db.session.add(Note(host=host, service=service, xtype='cpe', data=json.dumps(["cpe:/o:microsoft:windows_nt:3.5.1"])))
    db.session.add(Note(host=host, service=service, xtype='manual', data='some other note data'))

    # storage test data host2
    host = Host(
        address='127.3.3.3',
        hostname='testhost1.testdomain.test',
        os='Test Linux 2',
        comment='another server'
    )
    db.session.add(host)

    db.session.add(Service(
        host=host,
        proto='tcp',
        port=12345,
        state='closed:testreason',
        name='svcx'
    ))

    db.session.add(Vuln(
        host=host,
        name='test vulnerability',
        xtype='testxtype.123',
        severity=SeverityEnum.CRITICAL,
        comment='a test vulnerability comment',
        refs=['ref1', 'ref2'],
        tags=['tag1', 'tag2']
    ))

    db.session.add(Vuln(
        host=host,
        name='another test vulnerability',
        xtype='testxtype.124',
        severity=SeverityEnum.HIGH,
        comment='another vulnerability comment',
        tags=None
    ))

    db.session.add(Vuln(
        host=host,
        name='vulnerability1',
        xtype='testxtype.124',
        severity=SeverityEnum.MEDIUM,
        tags=['info']
    ))

    db.session.add(Vuln(
        host=host,
        name='vulnerability2',
        xtype='testxtype.124',
        severity=SeverityEnum.LOW,
        tags=['report']
    ))

    db.session.add(Vuln(
        host=host,
        name='vulnerability2',
        xtype='testxtype.124',
        severity=SeverityEnum.INFO,
        tags=['info']
    ))

    db.session.add(Vuln(
        host=host,
        service=Service.query.first(),
        name='vulnerability3',
        xtype='testxtype.124',
        severity=SeverityEnum.UNKNOWN,
        tags=['report']
    ))

    db.session.add(Vuln(host=host, service=Service.query.first(), **aggregable_vuln))

    db.session.add(Note(
        host=host,
        xtype='sner.testnote',
        data='testnote data',
        comment='test note comment'
    ))


@click.group(name='dbx', help='sner.server db management')
def command():
    """db command container"""


@command.command(name='init', help='initialize database schema')
@with_appcontext
def init():  # pragma: no cover
    """initialize database schema"""

    db.create_all()


@command.command(name='init-data', help='put initial data to database')
@with_appcontext
def initdata():  # pylint: disable=too-many-statements
    """put initial data to database"""

    db.session.add(User(username='user1', active=True, roles=['user', 'operator', 'admin']))
    initdata_dev()
    initdata_sner()
    initdata_pentest()
    db.session.commit()


@command.command(name='remove', help='remove database (including var content)')
@with_appcontext
def remove():
    """db remove command stub"""

    db_remove()
