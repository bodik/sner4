# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.task tests
"""

import json
from http import HTTPStatus
from pathlib import Path

from flask import url_for

from sner.server.scheduler.models import Task


def test_task_list_route(cl_operator):
    """task list route test"""

    response = cl_operator.get(url_for('scheduler.task_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_task_list_json_route(cl_operator, task):
    """task list_json route test"""

    response = cl_operator.post(
        url_for('scheduler.task_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': task.name}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == task.name

    response = cl_operator.post(
        url_for('scheduler.task_list_json_route', filter=f'Task.name=="{task.name}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == task.name


def test_task_add_route(cl_operator, task_factory):
    """task add route test"""

    atask = task_factory.build()

    form = cl_operator.get(url_for('scheduler.task_add_route')).form
    form['name'] = atask.name
    form['module'] = atask.module
    form['params'] = atask.params
    form['group_size'] = atask.group_size
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    ttask = Task.query.filter(Task.name == atask.name).one()
    assert ttask.name == atask.name
    assert ttask.module == atask.module
    assert ttask.params == atask.params
    assert ttask.group_size == atask.group_size


def test_task_edit_route(cl_operator, task):
    """task edit route test"""

    form = cl_operator.get(url_for('scheduler.task_edit_route', task_id=task.id)).form
    form['name'] = f'{form["name"].value} edited'
    form['params'] = f'{form["params"].value} added_parameter'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    ttask = Task.query.get(task.id)
    assert ttask.name == form['name'].value
    assert 'added_parameter' in ttask.params


def test_task_delete_route(cl_operator, job_completed):
    """task delete route test"""

    assert Path(job_completed.queue.data_abspath)

    form = cl_operator.get(url_for('scheduler.task_delete_route', task_id=job_completed.queue.task.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Task.query.get(job_completed.queue.task.id)
    assert not Path(job_completed.queue.data_abspath).exists()
