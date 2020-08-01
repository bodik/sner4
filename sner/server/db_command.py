# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
sner.server db command module
"""

import os
import shutil

import click
from flask import current_app
from flask.cli import with_appcontext

from sner.server.auth.models import User
from sner.server.extensions import db
from sner.server.scheduler.models import Excl, ExclFamily, Queue, Target
from sner.server.storage.models import Host, Note, Service, SeverityEnum, Vuln
from sner.server.utils import yaml_dump


def db_remove():
    """remove database artefacts (including var content)"""

    db.session.close()
    db.drop_all()

    path = current_app.config['SNER_VAR']
    for file_object in os.listdir(path):
        file_object_path = os.path.join(path, file_object)
        if os.path.isdir(file_object_path):
            shutil.rmtree(file_object_path)
        else:
            os.unlink(file_object_path)


@click.group(name='db', help='sner.server db management')
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

    # auth test data
    db.session.add(User(username='user1', active=True, roles=['user', 'operator', 'admin']))

    # scheduler test data
    db.session.add(Excl(family=ExclFamily.network, value='127.66.66.0/26', comment='blacklist 1'))
    db.session.add(Excl(family=ExclFamily.regex, value=r'.*donotscan.*', comment='blacklist 2'))

    queue = Queue(
        name='dev dummy',
        config=yaml_dump({'module': 'dummy', 'args': '--dummyparam 1'}),
        group_size=3,
        priority=10,
        active=True
    )
    db.session.add(queue)
    for target in range(100):
        db.session.add(Target(target=target, queue=queue))

    queue = Queue(
        name='pentest dns recon',
        config=yaml_dump({'module': 'nmap', 'args': '-sL -Pn'}),
        group_size=20,
        priority=10,
    )
    db.session.add(queue)
    for target in range(100):
        db.session.add(Target(target='10.0.0.%d' % target, queue=queue))

    db.session.add(Queue(
        name='pentest full syn scan',
        config=yaml_dump({
            'module': 'nmap',
            'args': '-sS -A -p1-65535 -Pn  --max-retries 3 --script-timeout 10m --min-hostgroup 20 --min-rate 900 --max-rate 1500'
        }),
        group_size=20,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner_disco ack scan top1000',
        config=yaml_dump({'module': 'nmap', 'args': '-sA --top-ports 1000 -Pn', 'timing_perhost': 10}),
        group_size=400,
        priority=12,
    ))

    db.session.add(Queue(
        name='sner_disco ack scan top10000',
        config=yaml_dump({'module': 'nmap', 'args': '-sA --top-ports 10000 -Pn', 'timing_perhost': 8}),
        group_size=1000,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner_data version scan basic',
        config=yaml_dump({'module': 'manymap', 'args': '-sV --version-intensity 4 -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_data version scan intense',
        config=yaml_dump({'module': 'manymap', 'args': '-sV --version-intensity 8 -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_disco ipv6 dns discover',
        config=yaml_dump({'module': 'six_dns_discover', 'delay': 1}),
        group_size=1000,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner_disco ipv6 ack scan top10000',
        config=yaml_dump({'module': 'nmap', 'args': '-6 -sA --top-ports 10000 -Pn', 'timing_perhost': 8}),
        group_size=1000,
        priority=10,
    ))

    db.session.add(Queue(
        name='sner_data ipv6 version scan basic',
        config=yaml_dump({'module': 'manymap', 'args': '-6 -sV --version-intensity 4 -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_data script scan ftp-anon',
        config=yaml_dump({'module': 'manymap', 'args': '-sC --script ftp-anon.nse -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_data script scan http-title',
        config=yaml_dump({'module': 'manymap', 'args': '-sC --script http-title.nse -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_data script scan ldap-rootdse',
        config=yaml_dump({'module': 'manymap', 'args': '-sC --script ldap-rootdse.nse -Pn', 'delay': 10}),
        group_size=50,
        priority=15,
    ))

    db.session.add(Queue(
        name='sner_sweep ack scan portA',
        config=yaml_dump({'module': 'nmap', 'args': '-sA -p1099 -Pn', 'timing_perhost': 1}),
        group_size=4000,
        priority=50,
    ))

    db.session.add(Queue(
        name='sweep_sweep version scan basic',
        config=yaml_dump({'module': 'manymap', 'args': '-sV --version-intensity 4 -Pn', 'delay': 10}),
        group_size=50,
        priority=55,
    ))

    # storage test data
    host = Host(
        address='127.4.4.4',
        hostname='testhost.testdomain.test<script>alert(1);</script>',
        os='Test Linux 1',
        comment='a some unknown service server')
    db.session.add(host)

    db.session.add(Service(
        host=host,
        proto='tcp',
        port=12345,
        state='open:testreason',
        name='svcx',
        info='testservice banner',
        comment='manual testservice comment'))

    host = Host(
        address='127.3.3.3',
        hostname='testhost1.testdomain.test',
        os='Test Linux 2',
        comment='another server')
    db.session.add(host)

    db.session.add(Service(
        host=host,
        proto='tcp',
        port=12345,
        state='closed:testreason',
        name='svcx'))

    db.session.add(Vuln(
        host=host,
        name='test vulnerability',
        xtype='testxtype.123',
        severity=SeverityEnum.critical,
        comment='a test vulnerability comment',
        refs=['ref1', 'ref2'],
        tags=['tag1', 'tag2']))

    db.session.add(Vuln(
        host=host,
        name='another test vulnerability',
        xtype='testxtype.124',
        severity=SeverityEnum.high,
        comment='another vulnerability comment',
        tags=None))

    db.session.add(Vuln(
        host=host,
        name='vulnerability1',
        xtype='testxtype.124',
        severity=SeverityEnum.medium,
        tags=['info']))

    db.session.add(Vuln(
        host=host,
        name='vulnerability2',
        xtype='testxtype.124',
        severity=SeverityEnum.low,
        tags=['report']))

    db.session.add(Vuln(
        host=host,
        name='vulnerability2',
        xtype='testxtype.124',
        severity=SeverityEnum.info,
        tags=['info']))

    db.session.add(Vuln(
        host=host,
        service=Service.query.first(),
        name='vulnerability3',
        xtype='testxtype.124',
        severity=SeverityEnum.unknown,
        tags=['report']))

    db.session.add(Note(
        host=host,
        xtype='sner.testnote',
        data='testnote data',
        comment='test note comment'))

    db.session.commit()


@command.command(name='remove', help='remove database (including var content)')
@with_appcontext
def remove():
    """db remove command stub"""

    db_remove()
