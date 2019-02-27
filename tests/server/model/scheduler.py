"""scheduler test models"""

import datetime
import json
import pytest
import uuid
from sner.server.extensions import db
from sner.server.model.scheduler import Job, Queue, Target, Task

from tests.server import persist_and_detach


def create_test_task():
	"""test task data"""

	return Task(
		name='test task name',
		module='test',
		params='--arg1 abc --arg2')


def create_test_queue(a_test_task):
	"""test queue data"""

	return Queue(
		name='queue name',
		task=a_test_task,
		group_size=2,
		priority=10,
		active=False)


def create_test_target(a_test_queue):
	"""test target data"""

	return Target(
		target='testtarget',
		queue=a_test_queue)


def create_test_job(a_test_queue):
	"""test job data"""

	return Job(
		id=str(uuid.uuid4()),
		assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
		result=None,
		queue=a_test_queue,
		time_start=datetime.datetime.now(),
		time_end=datetime.datetime.now())


@pytest.fixture()
def fixture_test_task(app): # pylint: disable=unused-argument
	"""persistent test task"""

	test_task = persist_and_detach(create_test_task())
	tmpid = test_task.id
	yield test_task
	db.session.delete(Task.query.get(tmpid))
	db.session.commit()


@pytest.fixture()
def fixture_test_queue(app, fixture_test_task): # pylint: disable=redefined-outer-name,unused-argument
	"""persistent test queue"""

	test_queue = create_test_queue(fixture_test_task)
	persist_and_detach(test_queue)
	tmpid = test_queue.id
	yield test_queue
	db.session.delete(Queue.query.get(tmpid))
	db.session.commit()
