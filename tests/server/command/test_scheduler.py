"""scheduler commands tests"""

import json
from random import random
from sner.server import db
from sner.server.command.scheduler import scheduler_command
from sner.server.model.scheduler import Job, Queue, Task

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_job, create_test_queue, create_test_target, create_test_task


## misc commands tests

def test_enumips(runner):
	"""basic enumerator test"""

	result = runner.invoke(scheduler_command, ['enumips', '127.0.0.128/30'])
	assert result.exit_code == 0
	assert '127.0.0.129' in result.output
	assert '127.0.0.130' in result.output



## task commands tests

def test_task_list_command(runner, test_task):
	"""task list command test"""

	test_task.name += ' command list '+str(random())
	persist_and_detach(test_task)


	result = runner.invoke(scheduler_command, ['task_list'])
	assert result.exit_code == 0
	assert test_task.name in result.output


def test_task_add_command(runner):
	"""task add command test"""

	test_task = create_test_task()
	test_task.name += ' command add '+str(random())


	result = runner.invoke(scheduler_command, ['task_add', test_task.module, '--name', test_task.name, '--params', test_task.params])
	assert result.exit_code == 0

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task
	assert task.name == test_task.name


	db.session.delete(task)
	db.session.commit()


def test_task_delete_command(runner):
	"""job delete command test"""

	test_task = create_test_task()
	test_task.name += ' command delete '+str(random())
	persist_and_detach(test_task)


	result = runner.invoke(scheduler_command, ['task_delete', str(test_task.id)])
	assert result.exit_code == 0

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert not task



## queue commands tests

def test_queue_list_command(runner, test_queue):
	"""queue list command test"""

	test_queue.name += ' command list '+str(random())
	persist_and_detach(test_queue)


	result = runner.invoke(scheduler_command, ['queue_list'])
	assert result.exit_code == 0
	assert test_queue.name in result.output


def test_queue_add_command(runner, test_task):
	"""queue add command test"""

	test_queue = create_test_queue(test_task)
	test_queue.name += ' command add '+str(random())


	result = runner.invoke(scheduler_command, ['queue_add', str(test_queue.task.id), '--name', test_queue.name])
	assert result.exit_code == 0

	queue = Queue.query.filter(Queue.name == test_queue.name).one_or_none()
	assert queue
	assert queue.name == test_queue.name


	db.session.delete(queue)
	db.session.commit()


def test_queue_enqueue_command(runner, test_queue):
	"""queue enqueue route test"""

	test_queue.name += ' command enqueue '+str(random())
	persist_and_detach(test_queue)
	test_target = create_test_target(test_queue)


	result = runner.invoke(scheduler_command, ['queue_enqueue', str(test_queue.id), test_target.target])
	assert result.exit_code == 0

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert queue.targets[0].target == test_target.target


	db.session.delete(queue.targets[0])
	db.session.commit()


def test_queue_flush_command(runner, test_queue):
	"""queue flush route test"""

	test_queue.name += ' command flush '+str(random())
	persist_and_detach(test_queue)
	test_target = create_test_target(test_queue)
	persist_and_detach(test_target)
	tmpid = test_queue.id


	result = runner.invoke(scheduler_command, ['queue_flush', str(tmpid)])
	assert result.exit_code == 0


	queue = Queue.query.filter(Queue.id == tmpid).one_or_none()
	assert not queue.targets


def test_queue_delete_command(runner, test_task):
	"""queue delete command test"""

	test_queue = create_test_queue(test_task)
	test_queue.name = test_queue.name+' command delete '+str(random())
	persist_and_detach(test_queue)


	result = runner.invoke(scheduler_command, ['queue_delete', str(test_queue.id)])
	assert result.exit_code == 0

	queue = Queue.query.filter(Queue.id == test_queue.id).one_or_none()
	assert not queue



## job commands tests

def test_job_list_command(runner, test_job):
	"""job list command test"""

	test_job.assignment = json.dumps('{"module": "job list command %s"}'%str(random()))
	persist_and_detach(test_job)


	result = runner.invoke(scheduler_command, ['job_list'])
	assert result.exit_code == 0
	assert test_job.id in result.output


def test_job_delete_command(runner, test_queue):
	"""job delete command test"""

	test_job = create_test_job(test_queue)
	test_job.assignment = json.dumps('{"module": "job delete %s"}'%str(random()))
	persist_and_detach(test_job)


	result = runner.invoke(scheduler_command, ['job_delete', test_job.id])
	assert result.exit_code == 0

	job = Job.query.filter(Job.id == test_job.id).one_or_none()
	assert not job
