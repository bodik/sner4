"""selenium ui tests for storage.note component"""

from sner.server.model.storage import Note
from tests.selenium import dt_inrow_delete, dt_rendered


def test_list(live_server, selenium, test_note):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    dt_rendered(selenium, 'storage.note_list_route', 'note_list_table', test_note.comment)


def test_list_inrow_delete(live_server, selenium, test_note):  # pylint: disable=unused-argument
    """delete note inrow button"""

    dt_inrow_delete(selenium, 'storage.note_list_route', 'note_list_table')
    assert not Note.query.filter(Note.id == test_note.id).one_or_none()
