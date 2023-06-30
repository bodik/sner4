# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
misc server components tests
"""

import pytest

from flask_wtf import FlaskForm

from sner.server.forms import JSONField, TextAreaListField
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


def test_jsonfield(app):  # pylint: disable=unused-argument
    """test jsonfield"""

    class Xform(FlaskForm):
        """form test instance"""
        a = JSONField()

    form = Xform(DummyPostData({'a': []}))
    assert form.a.data is None

    form = Xform(DummyPostData({'a': ['["a"]']}))
    assert form.a.data == ["a"]

    form = Xform(DummyPostData({'a': ['[invalidjson']}))
    assert not form.validate()
    assert 'This field contains invalid JSON' in form.a.errors

    # triggers pre_validate exception handler, when form field is assigned by unserializable value
    form.a.data = Xform()
    with pytest.raises(ValueError):
        form.validate()
