# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
nessus output parser tests
"""

from sner.server.model.storage import Note
from sner.server.parser.nessus import NessusParser


def test_xxe(app):  # pylint: disable=unused-argument
    """check if parser resolves external entities"""

    NessusParser.import_file('tests/server/data/parser-nessus-xxe.xml')

    notes = Note.query.filter(Note.data.like('%xmlentityvalue%')).all()
    assert not notes
