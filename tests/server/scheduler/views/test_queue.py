# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
scheduler.views.queue tests
"""

import json
from http import HTTPStatus
from pathlib import Path

from flask import url_for

from sner.server.scheduler.models import Job, Queue


def test_queue_list_route(cl_operator):
    """queue list route test"""

    response = cl_operator.get(url_for('scheduler.queue_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_queue_list_json_route(cl_operator, queue):
    """queue list_json route test"""

    response = cl_operator.post(
        url_for('scheduler.queue_list_json_route'),
        {'draw': 1, 'start': 0, 'length': 1, 'search[value]': queue.name}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == queue.name

    response = cl_operator.post(
        url_for('scheduler.queue_list_json_route', filter=f'Queue.name=="{queue.name}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['name'] == queue.name


def test_queue_add_route(cl_operator, queue_factory):
    """queue add route test"""

    aqueue = queue_factory.build()

    form = cl_operator.get(url_for('scheduler.queue_add_route')).form
    form['name'] = aqueue.name
    form['config'] = aqueue.config
    form['group_size'] = aqueue.group_size
    form['priority'] = aqueue.priority
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tqueue = Queue.query.filter(Queue.name == aqueue.name).one()
    assert tqueue.name == aqueue.name


def test_queue_add_route_config_validation(cl_operator, queue_factory):
    """queue add route test"""

    aqueue = queue_factory.build()

    form = cl_operator.get(url_for('scheduler.queue_add_route')).form
    form['name'] = aqueue.name
    form['config'] = ''
    form['group_size'] = aqueue.group_size
    form['priority'] = aqueue.priority
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "Invalid YAML")]')

    form = response.form
    form['config'] = "module: 'notexist'"
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and text()="Invalid module specified"]')

    form = response.form
    form['config'] = "module: 'dummy'\nadditionalKey: 'value'\n"
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "Invalid config")]')


def test_queue_edit_route(cl_operator, queue):
    """queue edit route test"""

    form = cl_operator.get(url_for('scheduler.queue_edit_route', queue_id=queue.id)).form
    form['name'] = f'{form["name"].value} edited'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert Queue.query.get(queue.id).name == form['name'].value


def test_queue_enqueue_route(cl_operator, queue, target_factory):
    """queue enqueue route test"""

    atarget = target_factory.build(queue=queue)

    form = cl_operator.get(url_for('scheduler.queue_enqueue_route', queue_id=queue.id)).form
    form['targets'] = f'{atarget.target}\n \n '
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tqueue = Queue.query.get(queue.id)
    assert len(tqueue.targets) == 1
    assert tqueue.targets[0].target == atarget.target


def test_queue_flush_route(cl_operator, target):
    """queue flush route test"""

    queue_id = target.queue_id

    form = cl_operator.get(url_for('scheduler.queue_flush_route', queue_id=target.queue_id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Queue.query.get(queue_id).targets


def test_queue_prune_route(cl_operator, job_completed):
    """queue flush route test"""

    form = cl_operator.get(url_for('scheduler.queue_prune_route', queue_id=job_completed.queue_id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Job.query.filter(Job.queue_id == job_completed.queue_id).all()
    assert not Path(job_completed.output_abspath).exists()


def test_queue_delete_route(cl_operator, job_completed):
    """queue delete route test"""

    tqueue = Queue.query.get(job_completed.queue_id)
    assert Path(tqueue.data_abspath)

    form = cl_operator.get(url_for('scheduler.queue_delete_route', queue_id=tqueue.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not Queue.query.get(tqueue.id)
    assert not Path(tqueue.data_abspath).exists()
