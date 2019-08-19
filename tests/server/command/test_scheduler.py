# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler commands tests
"""

import os

from sner.server.command.scheduler import scheduler_command
from sner.server.model.scheduler import Job, Queue

from tests.server.model.scheduler import create_test_target


def test_enumips_command(runner, tmpworkdir):
    """basic enumerator test"""

    test_path = 'enumips.txt'
    with open(test_path, 'w') as ftmp:
        ftmp.write('127.0.0.132/30')

    result = runner.invoke(scheduler_command, ['enumips', '127.0.0.128/30', '--file', test_path])
    assert result.exit_code == 0

    assert '127.0.0.129' in result.output
    assert '127.0.0.130' in result.output
    assert '127.0.0.133' in result.output


def test_rangetocidr_command(runner, tmpworkdir):
    """range to cidr enumerator test"""

    result = runner.invoke(scheduler_command, ['rangetocidr', '127.0.0.0', '128.0.0.3'])
    assert result.exit_code == 0

    assert '127.0.0.0/8' in result.output
    assert '128.0.0.0/30' in result.output


def test_queue_enqueue_command(runner, tmpworkdir, test_queue):
    """queue enqueue command test"""

    test_target = create_test_target(test_queue)
    test_path = 'ips.txt'
    with open(test_path, 'w') as ftmp:
        ftmp.write(test_target.target)

    result = runner.invoke(scheduler_command, ['queue_enqueue', str(666), test_target.target])
    assert result.exit_code == 1

    result = runner.invoke(scheduler_command, ['queue_enqueue', str(test_queue.id), test_target.target])
    assert result.exit_code == 0
    assert Queue.query.filter(Queue.id == test_queue.id).one_or_none().targets[0].target == test_target.target

    result = runner.invoke(scheduler_command, ['queue_enqueue', str(test_queue.id), '--file', test_path])
    assert result.exit_code == 0
    assert len(Queue.query.filter(Queue.id == test_queue.id).one_or_none().targets) == 2

    result = runner.invoke(scheduler_command, ['queue_enqueue', str(test_queue.name), test_target.target])
    assert result.exit_code == 0
    assert len(Queue.query.filter(Queue.id == test_queue.id).one_or_none().targets) == 3


def test_queue_flush_command(runner, test_target):
    """queue flush command test"""

    test_queue_id = test_target.queue_id

    result = runner.invoke(scheduler_command, ['queue_flush', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(scheduler_command, ['queue_flush', str(test_queue_id)])
    assert result.exit_code == 0

    queue = Queue.query.filter(Queue.id == test_queue_id).one_or_none()
    assert not queue.targets


def test_queue_prune_command(runner, test_job_completed):
    """queue prune command test"""

    test_job_completed_output_abspath = Job.query.get(test_job_completed.id).output_abspath

    result = runner.invoke(scheduler_command, ['queue_prune', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(scheduler_command, ['queue_prune', str(test_job_completed.queue_id)])
    assert result.exit_code == 0

    assert not Job.query.filter(Job.queue_id == test_job_completed.queue_id).all()
    assert not os.path.exists(test_job_completed_output_abspath)
