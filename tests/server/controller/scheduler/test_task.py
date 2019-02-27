"""controller task tests"""

from flask import url_for
from http import HTTPStatus
from random import random
from sner.server.extensions import db
from sner.server.model.scheduler import Target, Task

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_target, create_test_task, model_test_profile # pylint: disable=unused-import


def test_task_list_route(client):
	"""list route test"""

	response = client.get(url_for('scheduler.task_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Tasks list' in response


def test_task_add_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""add route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' add '+str(random())
	test_task.profile = model_test_profile
	test_target = create_test_target()


	form = client.get(url_for('scheduler.task_add_route')).form
	form['name'] = test_task.name
	form['profile'] = test_task.profile.id
	form['group_size'] = test_task.group_size
	form['priority'] = test_task.priority
	form['targets_field'] = '\n'.join([test_target.target])
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task is not None
	assert task.name == test_task.name
	assert task.targets[0].target == test_target.target


	db.session.delete(task)
	db.session.commit()


def test_task_edit_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""edit route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' edit '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)


	form = client.get(url_for('scheduler.task_edit_route', task_id=test_task.id)).form
	form['name'] = form['name'].value+' edited'
	form['targets_field'] = form['targets_field'].value+'\nadded target'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is not None
	assert task.name == form['name'].value
	assert task.modified > task.created
	assert 'added target' in [tmp.target for tmp in task.targets]


	db.session.delete(task)
	db.session.commit()


def test_task_delete_route(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""delete route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' delete '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)


	form = client.get(url_for('scheduler.task_delete_route', task_id=test_task.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is None


def test_task_targets_route_schedule(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""targets schedule route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' schedule '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)
	tmpid = test_task.id


	form = client.get(url_for('scheduler.task_targets_route', task_id=test_task.id, action='schedule')).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task.targets[0].scheduled


	db.session.delete(task)
	db.session.commit()


def test_task_targets_route_unschedule(client, model_test_profile): # pylint: disable=redefined-outer-name
	"""targets unschedule route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' unschedule '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)
	tmpid = test_task.id


	form = client.get(url_for('scheduler.task_targets_route', task_id=test_task.id, action='unschedule')).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == tmpid).one_or_none()
	assert not task.targets[0].scheduled


	db.session.delete(task)
	db.session.commit()
