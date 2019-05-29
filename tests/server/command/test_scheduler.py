"""scheduler commands tests"""

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


def test_queue_list_command(runner, test_queue):
    """queue list command test"""

    result = runner.invoke(scheduler_command, ['queue_list'])
    assert result.exit_code == 0
    assert test_queue.name in result.output


def test_queue_enqueue_command(runner, tmpworkdir, test_queue):
    """queue enqueue route test"""

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
    """queue flush route test"""

    test_queue_id = test_target.queue_id

    result = runner.invoke(scheduler_command, ['queue_flush', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(scheduler_command, ['queue_flush', str(test_queue_id)])
    assert result.exit_code == 0

    queue = Queue.query.filter(Queue.id == test_queue_id).one_or_none()
    assert not queue.targets


def test_job_list_command(runner, test_job):
    """job list command test"""

    result = runner.invoke(scheduler_command, ['job_list'])
    assert result.exit_code == 0
    assert test_job.id in result.output


def test_job_delete_command(runner, test_job):
    """job delete command test"""

    result = runner.invoke(scheduler_command, ['job_delete', str(666)])
    assert result.exit_code == 1

    result = runner.invoke(scheduler_command, ['job_delete', test_job.id])
    assert result.exit_code == 0

    job = Job.query.filter(Job.id == test_job.id).one_or_none()
    assert not job
