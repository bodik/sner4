# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.models tests
"""


def test_models_storage_repr(app, test_host, test_service, test_vuln, test_note):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(test_host)
    assert repr(test_service)
    assert repr(test_vuln)
    assert repr(test_note)
