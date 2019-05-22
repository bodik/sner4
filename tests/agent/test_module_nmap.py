"""agent module dummy tests"""

from zipfile import ZipFile

import pytest

from sner.agent import main
from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job, Queue, Target, Task
from tests import persist_and_detach


@pytest.fixture
def test_nmap_target():
    """queue target fixture"""

    task = Task(name='test task', module='nmap', params='-sL')
    persist_and_detach(task)
    queue = Queue(name='test queue', task=task, group_size=1, priority=10)
    persist_and_detach(queue)
    target = Target(target='127.0.0.1', queue=queue)
    yield persist_and_detach(target)


def test_basic(live_server, test_nmap_target):  # pylint: disable=redefined-outer-name
    """nmap module execution test"""

    result = main(['--server', live_server.url(), '--debug', '--queue', str(test_nmap_target.queue_id), '--oneshot'])
    assert result == 0

    job = Job.query.filter(Job.queue_id == test_nmap_target.queue_id).one_or_none()
    assert job
    with ZipFile(job_output_filename(job.id)) as ftmp_zip:
        with ftmp_zip.open('output.gnmap') as ftmp:
            assert 'Host: 127.0.0.1 (localhost)' in ftmp.read().decode('utf-8')
