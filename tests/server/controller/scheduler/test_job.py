"""controller job tests"""

import json
from flask import url_for
from http import HTTPStatus
from random import random
from sner.server.extensions import db
from sner.server.model.scheduler import Job, Queue

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_job, create_test_target, fixture_test_queue, fixture_test_task # pylint: disable=unused-import


def test_job_list_route(client):
	"""job list route test"""

	response = client.get(url_for('scheduler.job_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Jobs list' in response


def test_job_assign_route(client, fixture_test_queue): # pylint: disable=redefined-outer-name
	"""job assign route test"""

	test_target = create_test_target(fixture_test_queue)
	test_target.target += 'job assign '+str(random())
	persist_and_detach(test_target)


	response = client.get(url_for('scheduler.job_assign_route', queue_id=fixture_test_queue.id))
	assert response.status_code == HTTPStatus.OK
	assert isinstance(json.loads(response.body.decode('utf-8')), dict)

	queue = Queue.query.filter(Queue.id == fixture_test_queue.id).one_or_none()
	assert len(queue.jobs) == 1


	db.session.delete(queue.jobs[0])
	db.session.commit()


def test_job_delete_route(client, fixture_test_queue): # pylint: disable=redefined-outer-name
	"""delete route test"""

	test_job = create_test_job(fixture_test_queue)
	test_job.assignment = json.dumps('{"module": "job delete %s"}'%str(random()))
	persist_and_detach(test_job)


	form = client.get(url_for('scheduler.job_delete_route', job_id=test_job.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	job = Job.query.filter(Job.id == test_job.id).one_or_none()
	assert not job
