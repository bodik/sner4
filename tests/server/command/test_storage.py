"""storage commands tests"""

import json
import re

import pytest

from sner.server import db
from sner.server.command.storage import storage_command
from sner.server.model.storage import Host, Note


def test_import_nmap_command(runner):
	"""test nmap parser"""

	result = runner.invoke(storage_command, ['import', 'tests/server/data/parser-nmap-output.xml'])
	assert result.exit_code == 0

	host_id = re.search(r'parsed host: <Host (?P<hostid>\d+):', result.output).group('hostid')
	host = Host.query.filter(Host.id == host_id).one_or_none()
	assert host
	assert host.os == 'Linux 3.8 - 4.6'
	assert sorted([x.port for x in host.services]) == [22, 25, 139, 445, 5432]
	tmpnote = Note.query.filter(Note.host == host, Note.ntype == 'nmap.smtp-commands.tcp.25').one_or_none()
	assert "PIPELINING" in json.loads(tmpnote.data)["output"]


	db.session.delete(host)
	db.session.commit()


@pytest.mark.skip(reason='would note test flushing database')
def test_flush_command():
	"""flush storage database; no separate test db, test not implemented"""
	pass
