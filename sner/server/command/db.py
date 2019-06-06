"""db commands"""

import os
import shutil

import click
from flask import current_app
from flask.cli import with_appcontext
from sner.server import db
from sner.server.model.scheduler import Queue, Task, Target
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln


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
def db_command():
    """db command group/container"""


@db_command.command(name='init', help='initialize database schema')
@with_appcontext
def db_init():  # pragma: no cover
    """initialize database schema"""

    db.create_all()


@db_command.command(name='initdata', help='put initial data to database')
@with_appcontext
def db_initdata():
    """put initial data to database"""

    # scheduler test data
    db.session.add(Task(
        name='dummy',
        module='dummy',
        params='--dummyparam 1'))

    # basic nmap module scanning
    db.session.add(Task(
        name='dns recon',
        module='nmap',
        params='-Pn --reason   -sL'))

    db.session.add(Task(
        name='default scan',
        module='nmap',
        params='-Pn --reason   -A'))

    db.session.add(Task(
        name='full tcp scan',
        module='nmap',
        params='-Pn --reason   -sS -A -p1-65535   --min-hostgroup 16 --min-rate 900 --max-rate 1500 --max-retries 3'))

    db.session.add(Task(
        name='basic udp scan',
        module='nmap',
        params='-Pn --reason   -sU -sV   --min-hostgroup 16 --min-rate 900 --max-rate 1500 --max-retries 3'))

    db.session.add(Task(
        name='userspace tcp',
        module='nmap',
        params='-Pn --reason   -sT -A   --min-hostgroup 16 --min-rate 100 --max-rate 200'))

    # development queues with default targets
    queue = Queue(name='dummy', task=Task.query.filter(Task.name == 'dummy').one(), group_size=3, priority=10, active=True)
    db.session.add(queue)
    for target in range(100):
        db.session.add(Target(target=target, queue=queue))

    queue = Queue(name='dns recon', task=Task.query.filter(Task.name == 'dns recon').one(), group_size=16, priority=10, active=False)
    db.session.add(queue)
    for target in range(100):
        db.session.add(Target(target='10.0.0.%d' % target, queue=queue))

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
        name='testservice',
        info='testservice banner',
        comment='manual testservice comment'))

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


@db_command.command(name='remove', help='remove database (including var content)')
@with_appcontext
def db_remove_command():
    """db remove command stub"""

    db_remove()
