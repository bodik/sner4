"""agent basic tests"""

import json
import os
from uuid import uuid4
from zipfile import ZipFile

from sner.agent import main as agent_main
from sner.server.controller.scheduler.job import job_output_filename
from sner.server.model.scheduler import Job


def test_commandline_assignment(tmpworkdir, test_dummy_a):
    """test custom assignment passed from command line"""

    result = agent_main(['--assignment', json.dumps(test_dummy_a)])
    assert result == 0
    assert os.path.exists(test_dummy_a['id'])


def test_exception_in_module(tmpworkdir):
    """test exception handling during agent module execution"""

    test_a = {'id': str(uuid4()), 'module': 'notexist', 'params': '', 'targets': []}

    result = agent_main(['--assignment', json.dumps(test_a)])
    assert result == 1
    assert os.path.exists(test_a['id'])


def test_run_with_liveserver(tmpworkdir, live_server, test_dummy_target):
    """test basic agent's networking codepath; fetch, execute, pack and upload assignment"""

    result = agent_main(['--server', live_server.url(), '--debug', '--queue', str(test_dummy_target.queue_id), '--oneshot'])
    assert result == 0

    job = Job.query.filter(Job.queue_id == test_dummy_target.queue_id).one_or_none()
    assert job
    with ZipFile(job_output_filename(job.id)) as ftmp_zip:
        with ftmp_zip.open('assignment.json') as ftmp:
            assert test_dummy_target.target in ftmp.read().decode('utf-8')
