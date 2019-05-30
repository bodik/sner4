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
