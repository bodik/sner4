"""controller task tests"""

import pytest
from flask import url_for
from http import HTTPStatus
from random import random
from sner_web.extensions import db
from ..models import Task, ScheduledTarget
from ..tests import persist_and_detach
from ..tests.test_profile import model_test_profile # pylint: disable=unused-import


def create_test_task():
	"""test task data"""
	return Task(
		name='task name',
		targets=['1', '2', '3'],
		group_size=2,
		priority=10)


@pytest.fixture(scope='session')
def model_test_task(app, model_test_profile): # pylint: disable=redefined-outer-name
	"""persistent test task"""
	test_task = create_test_task()
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	yield test_task
	test_task = Task.query.get(test_task.id)
	db.session.delete(test_task)
	db.session.commit()


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
	form['profile'] = test_task.profile.id
	form['targets'] = '\n'.join(test_task.targets)
	form['group_size'] = test_task.group_size
	form['priority'] = test_task.priority
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


def test_targets_route_schedule(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""targets schedule route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' schedule '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)


	form = client.get(url_for('task.targets_route', task_id=test_task.id, action='schedule')).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	scheduled_targets = ScheduledTarget.query.filter(ScheduledTarget.task == test_task).all()
	assert len(scheduled_targets) is len(test_task.targets)


	for item in scheduled_targets:
		db.session.delete(item)
	db.session.delete(test_task)
	db.session.commit()



def test_targets_route_unschedule(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""targets unschedule route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' unschedule '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_scheduled_target = ScheduledTarget(target='testtarget')
	test_scheduled_target.task = test_task
	persist_and_detach(test_scheduled_target)


	form = client.get(url_for('task.targets_route', task_id=test_task.id, action='unschedule')).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	scheduled_targets = ScheduledTarget.query.filter(ScheduledTarget.task == test_task).all()
	assert not scheduled_targets


	db.session.delete(test_task)
	db.session.commit()
