"""controller task tests"""

from flask import url_for
from http import HTTPStatus
from random import random
from sner_web.extensions import db
from sner_web.models import Task
from sner_web.tests import persist_and_detach
from sner_web.tests.test_profile import model_test_profile # pylint: disable=unused-import


def create_test_task():
	"""test task data"""
	return Task(
		name='task name',
		priority=10,
		targets=['1', '2', '3'])


def test_list_route(client):
	"""list route test"""

	response = client.get(url_for('task.list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Tasks list' in response


def test_add_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""add route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' add '+str(random())
	test_task.profile = model_test_profile


	form = client.get(url_for('task.add_route')).form
	form['name'] = test_task.name
	form['priority'] = test_task.priority
	form['profile'] = test_task.profile.id
	form['targets'] = '\n'.join(test_task.targets)
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task is not None
	assert task.name == test_task.name
	assert task.targets == test_task.targets


	db.session.delete(task)
	db.session.commit()


def test_edit_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""edit route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' edit '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)


	form = client.get(url_for('task.edit_route', task_id=test_task.id)).form
	form['name'] = form['name'].value+' edited'
	form['targets'] = form['targets'].value+'\nadded target'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is not None
	assert task.name == form['name'].value
	assert 'added target' in task.targets
	assert task.modified > task.created


	db.session.delete(task)
	db.session.commit()


def test_delete_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""delete route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' delete '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)


	form = client.get(url_for('task.delete_route', task_id=test_task.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is None
