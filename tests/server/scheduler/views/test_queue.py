# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.queue tests
"""

import json
import os
from http import HTTPStatus

from flask import url_for

from sner.server.scheduler.models import Job, Queue
from tests.server.scheduler.models import create_test_queue, create_test_target


def test_queue_list_route(cl_operator):
    """queue list route test"""

    response = cl_operator.get(url_for('scheduler.queue_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_queue_list_json_route(cl_operator, test_queue):
    """queue list_json route test"""

    response = cl_operator.post(url_for('scheduler.queue_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_queue.ident})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['ident'] == test_queue.ident

    response = cl_operator.post(
        url_for('scheduler.queue_list_json_route', filter='Queue.ident=="%s"' % (test_queue.ident)),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['ident'] == test_queue.ident


def test_queue_add_route(cl_operator, test_task):
    """queue add route test"""

    test_queue = create_test_queue(test_task)

    form = cl_operator.get(url_for('scheduler.queue_add_route')).form
    form['name'] = test_queue.name
    form['task'] = test_queue.task.id
    form['priority'] = test_queue.priority
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    queue = Queue.query.filter(Queue.name == test_queue.name).one()
    assert queue.name == test_queue.name

    form = cl_operator.get(url_for('scheduler.queue_add_route')).form
    form['name'] = test_queue.name
    form['task'] = test_queue.task.id
    form['priority'] = test_queue.priority
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Queue identifier must be unique."]')


def test_queue_edit_route(cl_operator, test_queue):
    """queue edit route test"""

    form = cl_operator.get(url_for('scheduler.queue_edit_route', queue_id=test_queue.id)).form
    form['name'] = form['name'].value+' edited'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert Queue.query.get(test_queue.id).name == form['name'].value


def test_queue_enqueue_route(cl_operator, test_queue):
    """queue enqueue route test"""

    test_target = create_test_target(test_queue)

    form = cl_operator.get(url_for('scheduler.queue_enqueue_route', queue_id=test_queue.id)).form
    form['targets'] = test_target.target + '\n \n '
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    queue = Queue.query.get(test_queue.id)
    assert len(queue.targets) == 1
    assert queue.targets[0].target == test_target.target


def test_queue_flush_route(cl_operator, test_target):
    """queue flush route test"""

    test_queue_id = test_target.queue_id

    form = cl_operator.get(url_for('scheduler.queue_flush_route', queue_id=test_queue_id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Queue.query.get(test_queue_id).targets


def test_queue_prune_route(cl_operator, test_job_completed):
    """queue flush route test"""

    test_job_completed_output_abspath = Job.query.get(test_job_completed.id).output_abspath

    form = cl_operator.get(url_for('scheduler.queue_prune_route', queue_id=test_job_completed.queue_id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Job.query.filter(Job.queue_id == test_job_completed.queue_id).all()
    assert not os.path.exists(test_job_completed_output_abspath)


def test_queue_delete_route(cl_operator, test_job_completed):
    """queue delete route test"""

    test_queue = Queue.query.get(test_job_completed.queue_id)
    test_queue_data_abspath = test_queue.data_abspath
    assert os.path.exists(test_queue_data_abspath)

    form = cl_operator.get(url_for('scheduler.queue_delete_route', queue_id=test_queue.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Queue.query.get(test_queue.id)
    assert not os.path.exists(test_queue_data_abspath)
