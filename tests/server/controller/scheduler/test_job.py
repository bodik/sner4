"""controller job tests"""

import json
from flask import url_for
from http import HTTPStatus
from sner.server.extensions import db
from sner.server.model.scheduler import Job, Task

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_job, model_test_profile, model_test_task # pylint: disable=unused-import


def test_job_list_route(client):
	"""list route test"""

	response = client.get(url_for('scheduler.job_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Jobs list' in response


def test_job_assign_route(client, model_test_task): # pylint: disable=redefined-outer-name
	"""assign route test"""

	test_task = model_test_task


	response = client.get(url_for('scheduler.job_assign_route', task_id=test_task.id))
	assert response.status_code == HTTPStatus.OK
	assert isinstance(json.loads(response.body.decode('utf-8')), dict)

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert len(task.jobs) == 1


	db.session.delete(task.jobs[0])
	db.session.commit()


def test_job_delete_route(client, model_test_task): # pylint: disable=redefined-outer-name
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
