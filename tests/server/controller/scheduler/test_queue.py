"""controller queue tests"""

from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.scheduler import Queue
from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_queue, create_test_target


def test_queue_list_route(client):
	"""queue list route test"""

	response = client.get(url_for('scheduler.queue_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Queues list' in response


def test_queue_add_route(client, test_task):
	"""queue add route test"""

	test_queue = create_test_queue(test_task)
	test_queue.name += ' add %f' % random()


	form = client.get(url_for('scheduler.queue_add_route')).form
	form['name'] = test_queue.name
	form['task'] = test_queue.task.id
	form['group_size'] = test_queue.group_size
	form['priority'] = test_queue.priority
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	queue = Queue.query.filter(Queue.name == test_queue.name).one_or_none()
	assert queue
	assert queue.name == test_queue.name


	db.session.delete(queue)
	db.session.commit()


def test_queue_edit_route(client, test_queue):
	"""queue edit route test"""

	test_queue.name += ' edit %f' % random()
	persist_and_detach(test_queue)


	form = client.get(url_for('scheduler.queue_edit_route', queue_id=test_queue.id)).form
	form['name'] = form['name'].value+' edited'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert queue.name == form['name'].value


def test_queue_enqueue_route(client, test_queue):
	"""queue enqueue route test"""

	test_queue.name += ' enqueue %f' % random()
	persist_and_detach(test_queue)
	test_target = create_test_target(test_queue)


	form = client.get(url_for('scheduler.queue_enqueue_route', queue_id=test_queue.id)).form
	form['targets'] = test_target.target
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert queue.targets[0].target == test_target.target


	db.session.delete(queue.targets[0])
	db.session.commit()


def test_queue_flush_route(client, test_queue):
	"""queue flush route test"""

	test_queue.name += ' flush %f' % random()
	persist_and_detach(test_queue)
	test_target = create_test_target(test_queue)
	persist_and_detach(test_target)


	form = client.get(url_for('scheduler.queue_flush_route', queue_id=test_queue.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert not queue.targets


def test_queue_delete_route(client, test_task):
	"""queue delete route test"""

	test_queue = create_test_queue(test_task)
	test_queue.name += ' delete %f' % random()
	persist_and_detach(test_queue)


	form = client.get(url_for('scheduler.queue_delete_route', queue_id=test_queue.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert not queue
