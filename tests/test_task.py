from flask import url_for
from http import HTTPStatus
from random import random
from sner_web.extensions import db
from sner_web.models import Task


def create_test_task():
	return Task(name="task name", targets=["1", "2", "3"])



def test_list(client):
	response = client.get(url_for("task.list"))
	assert response.status_code == HTTPStatus.OK
	assert b"<h1>Tasks list" in response



def test_add(client):
	test_task = create_test_task()
	test_task.name = test_task.name+" add "+str(random())


	form = client.get(url_for("task.add")).form
	form["name"] = test_task.name
	form["targets"] = "\n".join(test_task.targets)
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.name == test_task.name).one_or_none()
	assert task is not None
	assert task.name == test_task.name
	assert task.targets == test_task.targets


	db.session.delete(task)
	db.session.commit()



def test_edit(client):
	# create a test-specific testing data, might be replaced by fixtures but we got with this for now
	test_task = create_test_task()
	test_task.name = test_task.name+" edit "+str(random())
	db.session.add(test_task) # add the new object to session
	db.session.commit() # commit it's creating
	db.session.refresh(test_task) # refresh all attributes, eg. fetch at least it's assigned id
	db.session.expunge(test_task) # detach the object from session to have the independent data available for following testcase


	form = client.get(url_for("task.edit", id=test_task.id)).form
	form["name"] = form["name"].value+" edited"
	form["targets"] = form["targets"].value+"\nadded target"
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is not None
	assert task.name == form["name"].value
	assert "added target" in task.targets
	assert task.modified > task.created


	db.session.delete(task)
	db.session.commit()



def test_delete(client):
	test_task = create_test_task()
	test_task.name = test_task.name+" delete "+str(random())
	db.session.add(test_task)
	db.session.commit()
	db.session.refresh(test_task)
	db.session.expunge(test_task)


	form = client.get(url_for("task.delete", id=test_task.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	task = Task.query.filter(Task.id == test_task.id).one_or_none()
	assert task is None
