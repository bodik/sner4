# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
storage.models tests
"""


def test_models_storage_repr(app, host, service, vuln, note):  # pylint: disable=unused-argument
    """test models repr methods"""

    assert repr(host)
    assert repr(service)
    assert repr(vuln)
    assert repr(note)
