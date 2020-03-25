# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.forms tests
"""

from sner.server.storage.forms import NoteForm, VulnForm
from tests.server import DummyPostData


def test_forms_models_relations(app, test_service):  # pylint: disable=unused-argument
    """validate VulnForm invalid inputs"""

    for formcls in VulnForm, NoteForm:
        form = formcls(DummyPostData({'host_id': 666}))
        assert not form.validate()
        assert 'No such host' in form.errors['host_id']

        form = formcls(DummyPostData({'service_id': 666}))
        assert not form.validate()
        assert 'No such service' in form.errors['service_id']

        form = formcls(DummyPostData({'service_id': test_service.id}))
        assert not form.validate()
        assert 'Service does not belong to the host' in form.errors['service_id']
