import re
from typing import List
from packaging.specifiers import SpecifierSet, InvalidSpecifier


class InvalidFormatException(Exception):
    """
    This exception is thrown when the format is invalid.
    """


def parse(versions_input: str) -> List[SpecifierSet]:
    """
    Parses the input, which should have the following format:
    "versions_specifier1; versions_specifier2; ..."

    Supported operators for version specifiers are:
    '==' ('=' also works), '>', '>=', '<', '<=', '!='

    If you use ';' as a separator (e.g. ">=4.0; ==2.0"), then
    at least one of the specifiers must be met.
    But if you use ',' as a separator (e.g. ">=3.0, <4.0"), then
    all of the version specifications in this section must be met.
    So if the specification is ">=3.0, <4.0; ==5.0", then the version
    must either be in range <3.0, 4.0), or it must be equal to 5.0.

    Returns a tuple of product and version specification, which have
    a form of a list of SpecifierSets from packaging library.
    """
    version_specifiers = []
    for spec in versions_input.split(";"):
        # Recommended reading to understand this regex:
        # https://docs.python.org/3.8/library/re.html#index-23
        # https://docs.python.org/3.8/library/re.html#index-21
        #
        # If '=' is not surrounded by '=', '<', '>', '!' or '~' on
        # the left side, or by '=' on the right side, replace
        # it with '==' so it can be parsed using SpecifierSet.
        spec = re.sub("(?<![!=<>~])=(?![=])", "==", spec)
        try:
            version_specifiers.append(SpecifierSet(spec))
        except InvalidSpecifier:
            raise InvalidFormatException(
                'Invalid format: version specifier "' + spec +
                '" does not meet the format criteria.'
            )

    return version_specifiers


def is_in_version_range(version: str, extrainfo: str, specifiers: List[SpecifierSet]) -> bool:
    """
    Checks if the version is in the range specified by a list of SpecifierSets.
    If at least one of the specifiers matches the version, then the result
    is True, otherwise it is False.
    """
    # For now, this tool cannot say if the version is vulnerable, if the used
    # system is some kind of derivate of Red Hat Enterprise Linux, because they
    # fix older versions without adding "pX" (e.g. "p1") suffix like Debian.
    DISABLED_OPERATING_SYSTEMS = ["CentOS",
                                  "Scientific Linux",
                                  "Red Hat Enterprise Linux",
                                  "Rocky",
                                  "AlmaLinux",
                                  "Oracle Linux"]
    for system in DISABLED_OPERATING_SYSTEMS:
        if system.lower() in extrainfo.lower():
            return False

    # Recommended reading to understand this regex:
    # https://docs.python.org/3.8/library/re.html#index-22
    # https://docs.python.org/3.8/library/re.html#index-20
    #
    # Replaces 'p' with '.' if 'p' is surrounded by 0-9 from both sides.
    # Then it can be parsed correctly. This is often the case with
    # Debian patches fixing a vulnerability in an older version.
    version = re.sub("(?<=[0-9])p(?=[0-9])", ".", version)
    # Forget everything after the first space. (unnecessary details)
    # e.g.: '7.9p1 Debian 10+deb10u2' -> '7.9p1' -> '7.9.1'
    version = version.split(" ")[0]

    for specifier in specifiers:
        if version in specifier:
            return True
    return False
