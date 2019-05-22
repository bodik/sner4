"""nessus output parser tests"""

from sner.server.model.storage import Note
from sner.server.parser.nessus import NessusParser


def test_xxe(app):  # pylint: disable=unused-argument
    """check if parser resolves external entities"""

    with open('tests/server/data/parser-nessus-xxe.xml') as ftmp:
        NessusParser.data_to_storage(ftmp.read())

    notes = Note.query.filter(Note.data.like('%xmlentityvalue%')).all()
    assert not notes
