# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.models tests
"""

from sner.server.scheduler.models import Heatmap, Readynet


def test_scheduler_models_repr(app, queue, target, job, excl_network):  # noqa: E501  pylint: disable=unused-argument,too-many-arguments
    """test models repr methods"""

    assert repr(excl_network)
    assert repr(job)
    assert repr(queue)
    assert repr(target)
    assert repr(Readynet.query.first())  # created by target factory
    assert repr(Heatmap.query.first())  # created by non-complete job factory
