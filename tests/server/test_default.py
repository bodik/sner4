"""misc server components tests"""

from flask_wtf import FlaskForm

from sner.server.form import LinesField
from tests.server import DummyPostData


def test_linesfield(app):  # pylint: disable=unused-argument
    """tests linefield custom form field"""

    class Xform(FlaskForm):
        a = LinesField()

    form = Xform(DummyPostData({'a': 'a\nb'}))
    assert isinstance(form.a.data, list)
    assert len(form.a.data) == 2

    form = Xform(DummyPostData())
    assert isinstance(form.a.data, list)
    assert not form.a.data


def test_models_scheduler_repr(app, test_task, test_queue, test_target, test_job):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_task)
    assert repr(test_queue)
    assert repr(test_target)
    assert repr(test_job)


def test_models_storage_repr(app, test_host, test_service, test_vuln, test_note):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_host)
    assert repr(test_service)
    assert repr(test_vuln)
    assert repr(test_note)
