from flask import url_for
from http import HTTPStatus
import pytest
from random import random
from sner_web.extensions import db
from sner_web.models import Profile
from sner_web.tests import persist_and_detach



def create_test_profile():
	return Profile( \
		name="test profile name",
		arguments="--arg1 abc --arg2")



@pytest.fixture(scope="session")
def model_test_profile(app):
	test_profile = persist_and_detach(create_test_profile())
	yield test_profile
	test_profile = Profile.query.get(test_profile.id)
	db.session.delete(test_profile)
	db.session.commit()



def test_list(client):
	response = client.get(url_for("profile.list"))
	assert response.status_code == HTTPStatus.OK
	assert b"<h1>Profiles list" in response



def test_add(client):
	test_profile = create_test_profile()
	test_profile.name = test_profile.name+" add "+str(random())


	form = client.get(url_for("profile.add")).form
	form["name"] = test_profile.name
	form["arguments"] = test_profile.arguments
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.name == test_profile.name).one_or_none()
	assert profile is not None
	assert profile.name == test_profile.name
	assert profile.arguments == test_profile.arguments


	db.session.delete(profile)
	db.session.commit()



def test_edit(client):
	# create a test-specific testing data, might be replaced by fixtures but we got with this for now
	test_profile = create_test_profile()
	test_profile.name = test_profile.name+" edit "+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for("profile.edit", id=test_profile.id)).form
	form["name"] = form["name"].value+" edited"
	form["arguments"] = form["arguments"].value+" added_argument"
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.id == test_profile.id).one_or_none()
	assert profile is not None
	assert profile.name == form["name"].value
	assert "added_argument" in profile.arguments
	assert profile.modified > profile.created


	db.session.delete(profile)
	db.session.commit()



def test_delete(client):
	test_profile = create_test_profile()
	test_profile.name = test_profile.name+" delete "+str(random())
	persist_and_detach(test_profile)


	form = client.get(url_for("profile.delete", id=test_profile.id)).form
	response = form.submit()
	assert response.status_code == HTTPStatus.FOUND

	profile = Profile.query.filter(Profile.id == test_profile.id).one_or_none()
	assert profile is None
