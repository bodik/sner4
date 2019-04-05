"""db commands"""

import click
from flask.cli import with_appcontext
from sner.server import db
from sner.server.model.scheduler import Queue, Task, Target
from sner.server.model.storage import Host, Note, Service, SeverityEnum, Vuln


@click.group(name='db', help='sner.server db management')
def db_command():
	"""db command group/container"""
	pass


@db_command.command(name='init', help='initialize database schema')
@with_appcontext
def db_init():
	"""initialize database schema"""

	db.create_all()


@db_command.command(name='initdata', help='put initial data to database')
@with_appcontext
def db_initdata():
	"""put initial data to database"""

## scheduler test data
	### dummy testing task and queue
	db.session.add(Task(
		name='dummy',
		module='dummy',
		params='--dummyparam 1'))


	### basic nmap module scanning
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


	### development queues with default targets
	queue = Queue(name='dummy', task=Task.query.filter(Task.name == 'dummy').one(), group_size=3, priority=10, active=True)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target=target, queue=queue))

	queue = Queue(name='fulltcp netx', task=Task.query.filter(Task.name == 'dns recon').one(), group_size=16, priority=10, active=False)
	db.session.add(queue)
	for target in range(100):
		db.session.add(Target(target='10.0.0.%d'%target, queue=queue))


## storage test data
	db.session.add(Host(
		address='127.4.4.4',
		hostname='testhost.testdomain.test<script>alert(1);</script>',
		os='Test Linux 1',
		comment='a some unknown service server'))

	db.session.add(Service(
		host=Host.query.filter(Host.address == '127.4.4.4').one_or_none(),
		proto='tcp',
		port=12345,
		state='open:testreason',
		name='testservice',
		info='testservice banner',
		comment='manual testservice comment'))

	db.session.add(Vuln(
		host=Host.query.filter(Host.address == '127.4.4.4').one_or_none(),
		name='test vulnerability',
		xtype='testxtype.123',
		severity=SeverityEnum.critical,
		comment='a test vulnerability comment',
		refs=['ref1', 'ref2']))

	db.session.add(Note(
		host=Host.query.filter(Host.address == '127.4.4.4').one_or_none(),
		ntype='sner.testnote',
		data='testnote data',
		comment='test note comment'))


	db.session.commit()
