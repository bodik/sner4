# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.commands tests
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import sner.server.scheduler.commands
from sner.server.scheduler.commands import command, PLANNER_DEFAULT_DATA_QUEUE
from sner.server.scheduler.models import Job, Queue, Target, Task
from sner.server.storage.models import Service
from tests import persist_and_detach
from tests.server.scheduler.models import create_test_target


def test_enumips_command(runner, tmpworkdir):  # pylint: disable=unused-argument
    """basic enumerator test"""

    test_path = 'enumips.txt'
    with open(test_path, 'w') as ftmp:
        ftmp.write('127.0.0.132/30\n')
        ftmp.write('127.0.1.123/32\n')

    result = runner.invoke(command, ['enumips', '127.0.0.128/30', '--file', test_path])
    assert result.exit_code == 0

    assert '127.0.0.129' in result.output
    assert '127.0.0.130' in result.output
    assert '127.0.0.133' in result.output
    assert '127.0.1.123' in result.output


def test_rangetocidr_command(runner):
    """range to cidr enumerator test"""

    result = runner.invoke(command, ['rangetocidr', '127.0.0.0', '128.0.0.3'])
    assert result.exit_code == 0

    assert '127.0.0.0/8' in result.output
    assert '128.0.0.0/30' in result.output


def test_queue_enqueue_command(runner, tmpworkdir, test_queue):  # pylint: disable=unused-argument
    """queue enqueue command test"""

    test_target = create_test_target(test_queue)
    test_path = 'ips.txt'
    with open(test_path, 'w') as ftmp:
        ftmp.write(test_target.target)
        ftmp.write('\n \n ')

    result = runner.invoke(command, ['queue-enqueue', str(666), test_target.target])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-enqueue', str(test_queue.id), test_target.target])
    assert result.exit_code == 0
    assert Queue.query.get(test_queue.id).targets[0].target == test_target.target

    result = runner.invoke(command, ['queue-enqueue', str(test_queue.id), '--file', test_path])
    assert result.exit_code == 0
    assert len(Queue.query.get(test_queue.id).targets) == 2

    result = runner.invoke(command, ['queue-enqueue', str(test_queue.ident), test_target.target])
    assert result.exit_code == 0
    assert len(Queue.query.get(test_queue.id).targets) == 3


def test_queue_flush_command(runner, test_target):
    """queue flush command test"""

    test_queue_id = test_target.queue_id

    result = runner.invoke(command, ['queue-flush', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-flush', str(test_queue_id)])
    assert result.exit_code == 0

    assert not Queue.query.get(test_queue_id).targets


def test_queue_prune_command(runner, test_job_completed):
    """queue prune command test"""

    test_job_completed_output_abspath = Job.query.get(test_job_completed.id).output_abspath

    result = runner.invoke(command, ['queue-prune', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-prune', str(test_job_completed.queue_id)])
    assert result.exit_code == 0

    assert not Job.query.filter(Job.queue_id == test_job_completed.queue_id).all()
    assert not Path(test_job_completed_output_abspath).exists()


def test_planner_command(runner):
    """test planner command"""

    dummy_assignment = '{"module": "dummy", "params": "", "targets":[]}'
    now = datetime.utcnow()

    test_disco_task_name, test_disco_queue_name = 'sner_900_disco.main'.split('.')
    test_disco_task = Task(name=test_disco_task_name, module='dummy', group_size=1)
    persist_and_detach(test_disco_task)
    test_disco_queue = Queue(task=test_disco_task, name=test_disco_queue_name, priority=10)
    persist_and_detach(test_disco_queue)
    test_disco_job = Job(id=str(uuid4()), queue=test_disco_queue, assignment=dummy_assignment, retval=0, time_start=now, time_end=now)
    tmp_job_output_path = Path(test_disco_job.output_abspath)
    tmp_job_output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_job_output_path.write_bytes(Path('tests/server/data/parser-nmap-job.zip').read_bytes())
    persist_and_detach(test_disco_job)

    default_data_task_name, default_data_queue_name = PLANNER_DEFAULT_DATA_QUEUE.split('.')
    default_data_task = Task(name=default_data_task_name, module='dummy', group_size=1)
    persist_and_detach(default_data_task)
    default_data_queue = Queue(task=default_data_task, name=default_data_queue_name, priority=10)
    persist_and_detach(default_data_queue)
    test_data_job = Job(id=str(uuid4()), queue=default_data_queue, assignment=dummy_assignment, retval=0, time_start=now, time_end=now)
    tmp_job_output_path = Path(test_data_job.output_abspath)
    tmp_job_output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_job_output_path.write_bytes(Path('tests/server/data/parser-manymap-job.zip').read_bytes())
    persist_and_detach(test_data_job)

    with patch.object(sner.server.scheduler.commands, 'PLANNER_LOOP_SLEEP', 0):
        result = runner.invoke(command, ['planner', '--oneshot'])
    assert result.exit_code == 0

    # simplified assertion
    assert Target.query.count() == 5
    assert Service.query.count() == 1
