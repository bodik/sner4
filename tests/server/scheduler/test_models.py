# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.models tests
"""


def test_scheduler_models_repr(app, queue, target, job, excl_network):  # noqa: E501  pylint: disable=unused-argument,too-many-arguments
    """test models repr methods"""

    assert repr(queue)
    assert repr(target)
    assert repr(job)
    assert repr(excl_network)
