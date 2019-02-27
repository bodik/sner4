"""controller profile tests"""

import pytest
from flask import url_for
from http import HTTPStatus
from random import random
from ..extensions import db
from ..models import Profile
from ..tests import persist_and_detach


def create_test_profile():
	"""test profile data"""
	return Profile(
		name='test profile name',
		module='test',
		params='--arg1 abc --arg2')


@pytest.fixture(scope='session')
def model_test_profile(app):
	"""persistent test profile"""
	test_profile = persist_and_detach(create_test_profile())
	yield test_profile
	test_profile = Profile.query.get(test_profile.id)
	db.session.delete(test_profile)
	db.session.commit()


def test_list_route(client):
	"""list route test"""

	response = client.get(url_for('profile.list_route'))
	assert response.status_code == HTTPStatus.OK
	assert b'<h1>Profiles list' in response


def test_add_route(client):
	"""add route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' add '+str(random())


	form = client.get(url_for('profile.add_route')).form
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


def test_edit_route(client):
	"""edit route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' edit '+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for('profile.edit_route', profile_id=test_profile.id)).form
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


def test_delete_route(client):
	"""delete route test"""

	test_profile = create_test_profile()
	test_profile.name = test_profile.name+' delete '+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for('profile.delete_route', profile_id=test_profile.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.id == test_profile.id).one_or_none()
	assert profile is None
