"""controller scheduler.task tests"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.scheduler import Task
from tests.server.model.scheduler import create_test_task


def test_task_list_route(cl_operator):
    """task list route test"""

    response = cl_operator.get(url_for('scheduler.task_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Tasks list' in response


def test_task_list_json_route(cl_operator, test_task):
    """task list_json route test"""

    response = cl_operator.post(url_for('scheduler.task_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_task.name})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == test_task.name

    response = cl_operator.post(
        url_for('scheduler.task_list_json_route', filter='Task.name=="%s"' % test_task.name),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == test_task.name


def test_task_add_route(cl_operator):
    """task add route test"""

    test_task = create_test_task()

    form = cl_operator.get(url_for('scheduler.task_add_route')).form
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


def test_task_edit_route(cl_operator, test_task):
    """task edit route test"""

    form = cl_operator.get(url_for('scheduler.task_edit_route', task_id=test_task.id)).form
    form['name'] = form['name'].value+' edited'
    form['params'] = form['params'].value+' added_parameter'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    task = Task.query.filter(Task.id == test_task.id).one_or_none()
    assert task
    assert task.name == form['name'].value
    assert 'added_parameter' in task.params


def test_task_delete_route(cl_operator, test_task):
    """task delete route test"""

    form = cl_operator.get(url_for('scheduler.task_delete_route', task_id=test_task.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    task = Task.query.filter(Task.id == test_task.id).one_or_none()
    assert not task
