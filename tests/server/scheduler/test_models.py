# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.models tests
"""


def test_scheduler_models_repr(app, test_task, test_queue, test_target, test_job, test_excl_network):  # noqa: E501  pylint: disable=unused-argument,too-many-arguments
    """test models repr methods"""

    assert repr(test_task)
    assert repr(test_queue)
    assert repr(test_target)
    assert repr(test_job)
    assert repr(test_excl_network)
