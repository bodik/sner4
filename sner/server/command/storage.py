"""storage commands"""

import os
from zipfile import ZipFile

import click
import magic
from flask import current_app
from flask.cli import with_appcontext

from sner.server import db
from sner.server.model.storage import Host
from sner.server.parser import registered_parsers


@click.group(name='storage', help='sner.server storage management')
def storage_command():
	"""storage commands click group/container"""
	pass


@storage_command.command(name='import', help='import data from files')
@with_appcontext
@click.argument('parser')
@click.argument('path', nargs=-1)
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
			try:
				parser_impl.data_to_storage(data_from_file(item, parser_impl))
			except Exception as e:
				current_app.logger.error('import \'%s\' failed: %s', item, e)


@storage_command.command(name='flush', help='flush all objects from storage')
@with_appcontext
def storage_flush():
	"""flush all objects from storage"""

	db.session.query(Host).delete()
	db.session.commit()
