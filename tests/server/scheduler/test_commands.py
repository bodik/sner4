# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.commands tests
"""

from pathlib import Path
from unittest.mock import patch

import sner.server.scheduler.commands
from sner.server.scheduler.commands import command, PLANNER_DEFAULT_DATA_QUEUE
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Service


def test_enumips_command(runner, tmpworkdir):  # pylint: disable=unused-argument
    """basic enumerator test"""

    apath = Path('enumips.txt')
    apath.write_text('127.0.0.132/30\n127.0.1.123/32\n')

    result = runner.invoke(command, ['enumips', '127.0.0.128/30', '--file', apath])
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


def test_queue_enqueue_command(runner, tmpworkdir, queue, target_factory):  # pylint: disable=unused-argument
    """queue enqueue command test"""

    atarget = target_factory.build(queue=queue)
    apath = Path('ips.txt')
    apath.write_text(f'{atarget.target}\n \n ')

    result = runner.invoke(command, ['queue-enqueue', 'notexist', atarget.target])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-enqueue', queue.name, atarget.target])
    assert result.exit_code == 0
    assert Queue.query.get(queue.id).targets[0].target == atarget.target

    result = runner.invoke(command, ['queue-enqueue', queue.name, '--file', apath])
    assert result.exit_code == 0
    assert len(Queue.query.get(queue.id).targets) == 2


def test_queue_flush_command(runner, target):
    """queue flush command test"""

    tqueue = Queue.query.get(target.queue_id)

    result = runner.invoke(command, ['queue-flush', 'notexist'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-flush', tqueue.name])
    assert result.exit_code == 0

    assert not Queue.query.get(tqueue.id).targets


def test_queue_prune_command(runner, job_completed):
    """queue prune command test"""

    result = runner.invoke(command, ['queue-prune', 'notexist'])
    assert result.exit_code == 1

    result = runner.invoke(command, ['queue-prune', job_completed.queue.name])
    assert result.exit_code == 0

    assert not Job.query.filter(Job.queue_id == job_completed.queue_id).all()
    assert not Path(job_completed.output_abspath).exists()


def test_planner_command(runner, queue_factory, job_completed_factory):
    """test planner command"""

    # disco job
    disco_queue = queue_factory.create(name='sner_900_disco')
    job_completed_factory.create(
        queue=disco_queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )

    # data job
    data_queue = queue_factory.create(name=PLANNER_DEFAULT_DATA_QUEUE)
    job_completed_factory.create(
        queue=data_queue,
        make_output=Path('tests/server/data/parser-manymap-job.zip').read_bytes()
    )

    # test itself
    with patch.object(sner.server.scheduler.commands, 'PLANNER_LOOP_SLEEP', 0):
        result = runner.invoke(command, ['planner', '--oneshot'])
    assert result.exit_code == 0

    # simplified assertion
    assert Target.query.count() == 5
    assert Service.query.count() == 1
