# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.task tests
"""

import json
import os
from http import HTTPStatus

from flask import url_for

from sner.server.scheduler.models import Queue, Task
from tests.server.scheduler.models import create_test_task


def test_task_list_route(cl_operator):
    """task list route test"""

    response = cl_operator.get(url_for('scheduler.task_list_route'))
    assert response.status_code == HTTPStatus.OK


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
    form['group_size'] = test_task.group_size
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    task = Task.query.filter(Task.name == test_task.name).one()
    assert task.name == test_task.name
    assert task.module == test_task.module
    assert task.params == test_task.params
    assert task.group_size == test_task.group_size

    form = cl_operator.get(url_for('scheduler.task_add_route')).form
    form['name'] = test_task.name
    form['module'] = test_task.module
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Must be unique."]')


def test_task_edit_route(cl_operator, test_task):
    """task edit route test"""

    form = cl_operator.get(url_for('scheduler.task_edit_route', task_id=test_task.id)).form
    form['name'] = form['name'].value+' edited'
    form['params'] = form['params'].value+' added_parameter'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    task = Task.query.get(test_task.id)
    assert task.name == form['name'].value
    assert 'added_parameter' in task.params


def test_task_delete_route(cl_operator, test_job_completed):
    """task delete route test"""

    test_queue = Queue.query.get(test_job_completed.queue_id)
    test_queue_data_abspath = test_queue.data_abspath
    test_task = Task.query.get(test_queue.task_id)
    assert os.path.exists(test_queue_data_abspath)

    form = cl_operator.get(url_for('scheduler.task_delete_route', task_id=test_task.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Task.query.get(test_task.id)
    assert not os.path.exists(test_queue_data_abspath)
