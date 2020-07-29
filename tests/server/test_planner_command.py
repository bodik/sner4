# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
planner command tests
"""

import multiprocessing
from pathlib import Path
from time import sleep

from sner.server.planner_command import command
from sner.server.scheduler.models import Target
from sner.server.storage.models import Host, Service
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
    result = runner.invoke(command, ['--oneshot'])
    assert result.exit_code == 0

    # simplified assertion
    assert Target.query.count() == 5
    assert Service.query.count() == 1


def test_planner_command_invalid_workflows(runner, queue_factory, job_completed_factory):
    """test invalid config handling inside planner"""

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

    # test itself
    result = runner.invoke(command, ['--oneshot'])
    assert result.exit_code == 0


def test_shutdown(runner):
    """test planner signaled shutdown"""

    proc = multiprocessing.Process(target=runner.invoke, args=(command, ['--loopsleep', '1']))
    proc.start()
    sleep(1)
    assert proc.is_alive()

    proc.terminate()
    sleep(1)
    assert not proc.is_alive()


def test_cleanups(runner, host_factory, service_factory):
    """test planners cleanup loop phase"""

    host1 = host_factory.create(address='127.127.127.135', os='identified')
    service_factory.create(host=host1, proto='tcp', port=1, state='open:reason')
    service_factory.create(host=host1, proto='tcp', port=1, state='filtered:reason')
    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)

    result = runner.invoke(command, ['--oneshot'])
    assert result.exit_code == 0

    hosts = Host.query.all()
    assert len(hosts) == 1
    services = Service.query.all()
    assert len(services) == 1
