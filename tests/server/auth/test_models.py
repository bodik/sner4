# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.models tests
"""


def test_auth_models_repr(app, user, webauthn_credential):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(user)
    assert repr(webauthn_credential)
