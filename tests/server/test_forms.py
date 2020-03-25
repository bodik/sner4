# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

from flask_wtf import FlaskForm

from sner.server.forms import TextAreaListField
from tests.server import DummyPostData


def test_textarealistfield(app):  # pylint: disable=unused-argument
    """tests TextAreaListField form field"""

    class Xform(FlaskForm):
        """form test instance"""
        a = TextAreaListField()

    form = Xform(DummyPostData({'a': 'a\nb'}))
    assert isinstance(form.a.data, list)
    assert len(form.a.data) == 2

    form = Xform(DummyPostData())
    assert isinstance(form.a.data, list)
    assert not form.a.data
