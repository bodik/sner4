# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
version parser, pulled from 713/logs/va2am
"""

import pytest

from sner.server.storage.version_parser import parse, is_in_version_range, InvalidFormatException


def test_invalid_version():
    """test parser"""

    with pytest.raises(InvalidFormatException):
        parse("3.0")
    with pytest.raises(InvalidFormatException):
        parse("!3.0")
    with pytest.raises(InvalidFormatException):
        parse("p3.0")
    # These should be parsed without an Exception:
    parse("!=3.0")
    parse("==3.0")
    parse("  =3.0")
    parse("=3.0")
    parse(" =3.0    ;  =4.0")
    parse(">=3.0")
    parse("   >3.0")
    parse(" <=3.0 ")
    parse("<3.0")


def test_is_in_version_range():
    """test parser in range"""

    version_spec = parse(">=3.0 ,  <4.0; =5.0 ")
    assert not is_in_version_range("5.1", version_spec)
    assert not is_in_version_range("4.0", version_spec)
    assert not is_in_version_range("2.3", version_spec)
    assert is_in_version_range("5.0", version_spec)
    assert is_in_version_range("3.0", version_spec)
    assert is_in_version_range("3.8", version_spec)
    assert is_in_version_range("3.3.3", version_spec)

    version_spec = parse("  >=3.0, <3.3; >=5.0.0")
    assert is_in_version_range("3.0", version_spec)
    assert is_in_version_range("3.1.3", version_spec)
    assert is_in_version_range("3.2.5", version_spec)
    assert is_in_version_range("5.0.1", version_spec)
    assert is_in_version_range("7.1.0", version_spec)
    assert not is_in_version_range("3.3", version_spec)
    assert not is_in_version_range("3.4", version_spec)
    assert not is_in_version_range("2.0", version_spec)
    assert not is_in_version_range("1.3.5", version_spec)
    assert not is_in_version_range("4.2", version_spec)

    # Debian patches.
    version_spec = parse(">4.0")
    assert is_in_version_range("4.0p1", version_spec)
    assert is_in_version_range("4.0p1 Debianblablabla", version_spec)
    assert not is_in_version_range("4.0", version_spec)
