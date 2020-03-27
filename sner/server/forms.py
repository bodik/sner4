# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared forms objects
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


class EmptyToNoneFieldMixin():  # pylint: disable=too-few-public-methods
    """empty string to none casting mixin"""

    # value from form
    def process_formdata(self, valuelist):
        """cast empty string to none"""
        if valuelist:
            self.data = None if valuelist[0] == '' else valuelist[0]  # pylint: disable=attribute-defined-outside-init


class StringNoneField(EmptyToNoneFieldMixin, StringField):
    """customized stringfield"""


class TextAreaNoneField(EmptyToNoneFieldMixin, TextAreaField):
    """customized textareafield"""


class ButtonForm(FlaskForm):
    """generic button form"""
