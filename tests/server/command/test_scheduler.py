"""command scheduler tests"""

from random import random
from sner.server.command.scheduler import scheduler_command
from sner.server.extensions import db
from sner.server.model.scheduler import Target, Task

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_target, create_test_task, model_test_profile # pylint: disable=unused-import


def test_task_list_command(runner, model_test_profile): # pylint: disable=redefined-outer-name
	"""task list command test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' command list '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)


	result = runner.invoke(scheduler_command, ['task_list'])
	assert result.exit_code == 0
	assert test_task.name in result.output


	db.session.delete(test_task)
	db.session.commit()


def test_task_add_command(runner, model_test_profile): # pylint: disable=redefined-outer-name
	"""task add command test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' command add '+str(random())
	test_task.profile = model_test_profile
	test_target = create_test_target()


	result = runner.invoke(scheduler_command, ['task_add', str(test_task.profile.id), '--name', test_task.name, test_target.target])
	assert result.exit_code == 0

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task is not None
	assert task.name == test_task.name
	assert task.targets[0].target == test_target.target


	db.session.delete(task)
	db.session.commit()


def test_task_delete_command(runner, model_test_profile): # pylint: disable=redefined-outer-name
	"""delete route test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' delete command '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)


	result = runner.invoke(scheduler_command, ['task_delete', str(test_task.id)])
	assert result.exit_code == 0

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is None


def test_task_targets_command_schedule(runner, model_test_profile): # pylint: disable=redefined-outer-name
	"""task schedule command test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' schedule command '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)
	tmpid = test_task.id


	result = runner.invoke(scheduler_command, ['task_targets', str(test_task.id), 'schedule'])
	assert result.exit_code == 0

	task = Task.query.filter(Task.id == tmpid).one_or_none()
	assert task.targets[0].scheduled


	db.session.delete(task)
	db.session.commit()


def test_task_targets_command_unschedule(runner, model_test_profile): # pylint: disable=redefined-outer-name
	"""task unschedule command test"""

	test_task = create_test_task()
	test_task.name = test_task.name+' unschedule command '+str(random())
	test_task.profile = model_test_profile
	persist_and_detach(test_task)
	test_target = create_test_target()
	test_target.task = test_task
	persist_and_detach(test_target)
	tmpid = test_task.id


	result = runner.invoke(scheduler_command, ['task_targets', str(test_task.id), 'unschedule'])
	assert result.exit_code == 0

	task = Task.query.filter(Task.id == tmpid).one_or_none()
	assert not task.targets[0].scheduled


	db.session.delete(task)
	db.session.commit()


def test_enumips(runner):
	"""basic enumerator test"""

	result = runner.invoke(scheduler_command, ['enumips', '127.0.0.128/30'])
	assert result.exit_code == 0
	assert '127.0.0.129' in result.output
	assert '127.0.0.130' in result.output
