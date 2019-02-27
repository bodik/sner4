"""controller job tests"""

import datetime
import json
import logging
import uuid
from flask import url_for
from http import HTTPStatus
from random import random
from sner.server.extensions import db
from sner.server.model.scheduler import Job, ScheduledTarget, Task
from .. import persist_and_detach
from .test_profile import model_test_profile # pylint: disable=unused-import
from .test_task import model_test_task # pylint: disable=unused-import


def create_test_job():
	"""test job data"""
	return Job(
		id=str(uuid.uuid4()),
		assignment=json.dumps({'module': 'testjob', 'targets': ['1', '2']}),
		targets=['1', '2'],
		time_start=datetime.datetime.now(),
		time_end=datetime.datetime.now())


def test_list_route(client):
	"""list route test"""

	response = client.get(url_for('scheduler.job_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Jobs list' in response


def test_assign_route(client, model_test_task):
	"""assign route test"""

	task = Task.query.filter(Task.id==model_test_task.id).one_or_none()
	db.session.add(ScheduledTarget(target=task.targets[0], task=task))
	db.session.commit()


	response = client.get(url_for('scheduler.job_assign_route', task_id=task.id))
	assert response.status_code == HTTPStatus.OK
	assert type(json.loads(response.body.decode('utf-8'))) is dict
	assert len(task.jobs) == 1

	
	db.session.delete(task.jobs[0])
	db.session.commit()


def test_delete_route(client, model_test_task):
	"""delete route test"""

	test_job = create_test_job()
	tmp = json.loads(test_job.assignment)
	tmp['module'] = 'delete '+tmp['module']
	test_job.assignment = json.dumps(tmp)
	test_job.task = model_test_task
	persist_and_detach(test_job)


	form = client.get(url_for('scheduler.job_delete_route', job_id=test_job.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	job = Job.query.filter(Job.id == test_job.id).one_or_none()
	assert job is None
