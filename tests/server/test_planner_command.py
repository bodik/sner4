# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner command tests
"""

from pathlib import Path
from unittest.mock import patch

import sner.server.planner_command
from sner.server.planner_command import command
from sner.server.scheduler.models import Target
from sner.server.storage.models import Service
from sner.server.utils import yaml_dump


def test_planner_command(runner, queue_factory, job_completed_factory):
    """test planner command"""

    # enqueue workflow
    disco_queue = queue_factory.create(
        name='test queue disco',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
        workflow=yaml_dump({'step': 'enqueue_servicelist', 'queue': 'test queue version scan'})
    )
    job_completed_factory.create(
        queue=disco_queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )

    # import workflow
    data_queue = queue_factory.create(
        name='test queue version scan',
        config=yaml_dump({'module': 'manymap', 'args': 'arg1'}),
        workflow=yaml_dump({'step': 'import'})
    )
    job_completed_factory.create(
        queue=data_queue,
        make_output=Path('tests/server/data/parser-manymap-job.zip').read_bytes()
    )

    # test itself
    with patch.object(sner.server.planner_command, 'PLANNER_LOOP_SLEEP', 0):
        result = runner.invoke(command, ['--oneshot'])
    assert result.exit_code == 0

    # simplified assertion
    assert Target.query.count() == 5
    assert Service.query.count() == 1


def test_planner_command_invalid_workflows(runner, queue_factory, job_completed_factory):
    """test invalid config handling inside planner"""

    invalid_workflow_yaml_queue = queue_factory.create(
        name='invalid_workflow_yaml_queue',
        config=yaml_dump({'module': 'dummy', 'args': 'arg1'}),
        workflow='invalid:\nyaml',
    )
    job_completed_factory.create(queue=invalid_workflow_yaml_queue, make_output=b'empty')

    invalid_workflow_step_queue = queue_factory.create(
        name='invalid_workflow_step_queue',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
        workflow=yaml_dump({'step': 'invalid'})
    )
    job_completed_factory.create(queue=invalid_workflow_step_queue, make_output=b'empty')

    invalid_parser_queue = queue_factory.create(
        name='invalid_parser_queue',
        config=yaml_dump({'module': 'dummy', 'args': 'arg1'}),
        workflow=yaml_dump({'step': 'import'})
    )
    job_completed_factory.create(queue=invalid_parser_queue, make_output=b'empty')

    invalid_next_queue = queue_factory.create(
        name='invalid_next_queue',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
        workflow=yaml_dump({'step': 'enqueue_servicelist', 'queue': 'notexist'})
    )
    job_completed_factory.create(queue=invalid_next_queue, make_output=b'empty')

    # test itself
    with patch.object(sner.server.planner_command, 'PLANNER_LOOP_SLEEP', 0):
        result = runner.invoke(command, ['--oneshot'])
    assert result.exit_code == 0
