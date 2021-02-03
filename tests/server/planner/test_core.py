# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner core tests
"""

import pytest
import yaml
from schema import SchemaError

from sner.server.planner.core import PIPELINE_CONFIG_SCHEMA, run_pipeline


def test_generic_pipeline(app):  # pylint: disable=unused-argument
    """test generic pipeline"""

    config = {
        'type': 'generic',
        'steps': []
    }

    run_pipeline(config)


def test_queue_pipeline(app):  # pylint: disable=unused-argument
    """test queue pipeline"""

    config = {
        'type': 'queue',
        'steps': [{'step': 'stop_pipeline'}]
    }

    run_pipeline(config)


def test_interval_pipeline(app):  # pylint: disable=unused-argument
    """test interval pipeline"""

    config = {
        'type': 'interval',
        'name': 'interval_test',
        'interval': '1h',
        'steps': [{'step': 'stop_pipeline'}]
    }

    run_pipeline(config)
    # trigger interval backoff branch, should not raise StopPipeline
    run_pipeline(config)


def test_invalid_pipeline_config():  # pylint: disable=unused-argument
    """test invalid config pipeline. very basic test for pipeline schema validation."""

    config = yaml.safe_load("""
        pipelines:
          - type: interval
            XXname: missing_proper_name
            interval: 120days
            steps: []
    """)

    with pytest.raises(SchemaError):
        PIPELINE_CONFIG_SCHEMA.validate(config['pipelines'][0])
