# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.models tests
"""


def test_auth_models_repr(app, test_user, test_wncred):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_user)
    assert repr(test_wncred)
