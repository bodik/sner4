"""storage commands"""

import click
import magic
import os

from flask.cli import with_appcontext
from zipfile import ZipFile

from sner.server import db
from sner.server.model.storage import Host
from sner.server.parser import registered_parsers


@click.group(name='storage', help='sner.server storage management')
def storage_command():
	"""storage commands click group/container"""
	pass


@storage_command.command(name='import', help='import data from files')
@with_appcontext
@click.argument('path', nargs=-1)
@click.option('--parser', default='nmap')
def storage_import(path, parser):
	"""import data"""

	def data_from_file(filename, pparser):
		with open(filename, 'rb') as ifile:
			mime_type = magic.detect_from_fobj(ifile).mime_type
			if mime_type == 'application/zip':
				with ZipFile(ifile, 'r') as ftmp:
					data = ftmp.read(pparser.JOB_OUTPUT_DATAFILE)
			else:
				data = ifile.read()
		return data.decode('utf-8')

	parser_impl = registered_parsers[parser]
	for item in path:
		if os.path.isfile(item):
			parser_impl.data_to_storage(data_from_file(item, parser_impl))


@storage_command.command(name='flush', help='flush all objects from storage')
@with_appcontext
def storage_flush():
	"""flush all objects from storage"""

	for host in Host.query.all():
		db.session.delete(host)
	db.session.commit()
