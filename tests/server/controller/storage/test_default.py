"""sner.server.controller.storage functions test"""

from sner.server.controller.storage import get_related_models
from sner.server.form.storage import NoteForm, VulnForm
from tests.server import DummyPostData


def test_get_related_models(app, test_service):  # pylint: disable=unused-argument
    """test function used to link new vuln/note to corresponding models"""

    host, service = get_related_models('host', test_service.host_id)
    assert host.id == test_service.host_id
    assert not service

    host, service = get_related_models('service', test_service.id)
    assert host.id == test_service.host_id
    assert service.id == test_service.id


def test_json_indent_filter(app):  # pylint: disable=unused-argument
    """test indenting filter"""

    assert app.jinja_env.filters['json_indent']('"xxx"') == '"xxx"'
    assert app.jinja_env.filters['json_indent']('xxx') == 'xxx'


def test_forms_models_relations(app, test_service):
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
