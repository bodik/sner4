# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
flask forms
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField


class TextAreaListField(TextAreaField):
    """textarea transparently handling list of items"""

    # value to form
    def _value(self):
        return '\n'.join(self.data) if self.data else ''

    # value from form
    def process_formdata(self, valuelist):
        self.data = valuelist[0].splitlines() if valuelist else []  # pylint: disable=attribute-defined-outside-init


class StringNoneField(StringField):
    """stringfield converting empty string to None"""

    # value from form
    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0] or None  # pylint: disable=attribute-defined-outside-init


class ButtonForm(FlaskForm):
    """generic button form"""
