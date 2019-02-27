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


def create_test_task(a_test_profile):
	"""test task data"""

	return Task(
		name='task name',
		profile=a_test_profile,
		group_size=2,
		priority=10,
		active=False)


def create_test_target(a_test_task):
	"""test target data"""

	return Target(
		target='testtarget',
		task=a_test_task)


def create_test_job(a_test_task):
	"""test job data"""

	return Job(
		id=str(uuid.uuid4()),
		assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
		result=None,
		task=a_test_task,
		targets=['1', '2'],
		time_start=datetime.datetime.now(),
		time_end=datetime.datetime.now())


@pytest.fixture()
def fixture_test_profile(app): # pylint: disable=unused-argument
	"""persistent test profile"""

	test_profile = persist_and_detach(create_test_profile())
	tmpid = test_profile.id
	yield test_profile
	db.session.delete(Profile.query.get(tmpid))
	db.session.commit()


@pytest.fixture()
def fixture_test_task(app, fixture_test_profile): # pylint: disable=redefined-outer-name,unused-argument
	"""persistent test task"""

	test_task = create_test_task(fixture_test_profile)
	persist_and_detach(test_task)
	tmpid = test_task.id
	yield test_task
	db.session.delete(Task.query.get(tmpid))
	db.session.commit()
