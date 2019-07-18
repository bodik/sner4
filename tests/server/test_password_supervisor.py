# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
run password supervisor tests
"""

from sner.server.password_supervisor import test_all


def test_password_supervisor():
    """run test_password_supervisor unit tests"""

    test_all()
