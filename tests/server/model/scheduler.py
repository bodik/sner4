"""scheduler test models"""

import datetime
import json
import pytest
import uuid
from sner.server.extensions import db
from sner.server.model.scheduler import Job, Profile, Target, Task

from tests.server import persist_and_detach


def create_test_profile():
	"""test profile data"""

	return Profile(
		name='test profile name',
		module='test',
		params='--arg1 abc --arg2')


@pytest.fixture(scope='session')
def model_test_profile(app): # pylint: disable=unused-argument
	"""persistent test profile"""

	test_profile = persist_and_detach(create_test_profile())
	tmpid = test_profile.id
	yield test_profile
	db.session.delete(Profile.query.get(tmpid))
	db.session.commit()


def create_test_task():
	"""test task data"""

	return Task(
		name='task name',
		group_size=2,
		priority=10)


@pytest.fixture(scope='session')
def model_test_task(app, model_test_profile): # pylint: disable=redefined-outer-name,unused-argument
	"""persistent test task"""

	test_task = create_test_task()
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	tmpid = test_task.id
	yield test_task
	db.session.delete(Task.query.get(tmpid))
	db.session.commit()


def create_test_target():
	"""test target data"""

	return Target(
		target='testtarget',
		scheduled=False)


def create_test_job():
	"""test job data"""

	return Job(
		id=str(uuid.uuid4()),
		assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
		targets=['1', '2'],
		time_start=datetime.datetime.now(),
		time_end=datetime.datetime.now())
