"""controller profile tests"""

from flask import url_for
from http import HTTPStatus
from random import random
from sner.server.extensions import db
from sner.server.model.scheduler import Profile

from tests.server import persist_and_detach
from tests.server.model.scheduler import create_test_profile


def test_profile_list_route(client):
	"""list route test"""

	response = client.get(url_for('scheduler.profile_list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Profiles list' in response


def test_profile_add_route(client):
	"""add route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' add '+str(random())


	form = client.get(url_for('scheduler.profile_add_route')).form
	form['name'] = test_profile.name
	form['module'] = test_profile.module
	form['params'] = test_profile.params
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.name == test_profile.name).one_or_none()
	assert profile is not None
	assert profile.name == test_profile.name
	assert profile.module == test_profile.module
	assert profile.params == test_profile.params


	db.session.delete(profile)
	db.session.commit()


def test_profile_edit_route(client):
	"""edit route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' edit '+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for('scheduler.profile_edit_route', profile_id=test_profile.id)).form
	form['name'] = form['name'].value+' edited'
	form['params'] = form['params'].value+' added_parameter'
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.id == test_profile.id).one_or_none()
	assert profile is not None
	assert profile.name == form['name'].value
	assert 'added_parameter' in profile.params
	assert profile.modified > profile.created


	db.session.delete(profile)
	db.session.commit()


def test_profile_delete_route(client):
	"""delete route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' delete '+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for('scheduler.profile_delete_route', profile_id=test_profile.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.id == test_profile.id).one_or_none()
	assert profile is None
