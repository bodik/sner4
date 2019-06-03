"""selenium ui tests for storage.note component"""

from flask import url_for

from sner.server.model.storage import Note
from tests.selenium import dt_inrow_delete, dt_rendered


def test_list(live_server, selenium, test_note):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    selenium.get(url_for('storage.note_list_route', _external=True))
    dt_rendered(selenium, 'note_list_table', test_note.comment)


def test_list_inrow_delete(live_server, selenium, test_note):  # pylint: disable=unused-argument
    """delete note inrow button"""

    selenium.get(url_for('storage.note_list_route', _external=True))
    dt_inrow_delete(selenium, 'note_list_table')
    assert not Note.query.filter(Note.id == test_note.id).one_or_none()
