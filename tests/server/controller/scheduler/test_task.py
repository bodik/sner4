"""controller profile tests"""

from http import HTTPStatus
from random import random

from flask import url_for

from sner.server import db
from sner.server.model.scheduler import Task
from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_task


def test_task_list_route(client):
	"""task list route test"""

	response = client.get(url_for('scheduler.task_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert '<h1>Tasks list' in response


def test_task_add_route(client):
	"""task add route test"""

	test_task = create_test_task()
	test_task.name += ' add %f' % random()


	form = client.get(url_for('scheduler.task_add_route')).form
	form['name'] = test_task.name
	form['module'] = test_task.module
	form['params'] = test_task.params
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task
	assert task.name == test_task.name
	assert task.module == test_task.module
	assert task.params == test_task.params


	db.session.delete(task)
	db.session.commit()


def test_task_edit_route(client, test_task):
	"""task edit route test"""

	test_task.name += ' edit %f' % random()
	persist_and_detach(test_task)


	form = client.get(url_for('scheduler.task_edit_route', task_id=test_task.id)).form
	form['name'] = form['name'].value+' edited'
	form['params'] = form['params'].value+' added_parameter'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task
	assert task.name == form['name'].value
	assert 'added_parameter' in task.params


def test_task_delete_route(client):
	"""task delete route test"""

	test_task = create_test_task()
	test_task.name += ' delete %f' % random()
	persist_and_detach(test_task)


	form = client.get(url_for('scheduler.task_delete_route', task_id=test_task.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert not task
