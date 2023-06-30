# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared forms objects
"""

import json

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

    # value from form
    def process_formdata(self, valuelist):
        """additionaly replace web line endings"""

        super().process_formdata(valuelist)
        if self.data:
            self.data = self.data.replace('\r\n', '\n')   # pylint: disable=attribute-defined-outside-init


class ButtonForm(FlaskForm):
    """generic button form"""


class JSONField(StringField):
    """json string field"""

    def _value(self):
        return json.dumps(self.data) if self.data else ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = json.loads(valuelist[0])  # pylint: disable=attribute-defined-outside-init
            except ValueError:
                raise ValueError('This field contains invalid JSON') from None
        else:
            self.data = None  # pylint: disable=attribute-defined-outside-init

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data:
            try:
                json.dumps(self.data)
            except TypeError:
                raise ValueError('This field contains invalid JSON') from None
