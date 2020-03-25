# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
shared objects for models
"""

from enum import Enum


class SelectableEnum(Enum):
    """base class for using enum as in select fields"""

    @classmethod
    def choices(cls):
        """from self/class generates list for SelectField"""
        return [(choice, choice.name) for choice in cls]

    @classmethod
    def coerce(cls, item):
        """casts input from submitted form back to the corresponding python object"""
        return cls(item) if not isinstance(item, cls) else item

    def __str__(self):
        return self.name
