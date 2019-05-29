"""sner.server.controller.storage functions test"""

from sner.server.controller.storage import get_related_models


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

    assert app.jinja_env.filters['json_indent']('"xxx"') ==  '"xxx"'
    assert app.jinja_env.filters['json_indent']('xxx') ==  'xxx'
