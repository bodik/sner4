# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
run sqlafilter parser tests
"""

from sner.server.sqlafilter import test_all


def test_sqlafilter_parser():
    """run sqlafilter unit tests"""

    test_all()
