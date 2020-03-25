# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
auth.views.user tests
"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.auth.models import User
from sner.server.password_supervisor import PasswordSupervisor as PWS
from tests.server import get_csrf_token
from tests.server.auth.models import create_test_user


def test_user_list_route(cl_admin):
    """user list route test"""

    response = cl_admin.get(url_for('auth.user_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_user_list_json_route(cl_admin, test_user):
    """user list_json route test"""

    response = cl_admin.post(url_for('auth.user_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': test_user.username})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['username'] == test_user.username

    response = cl_admin.post(
        url_for('auth.user_list_json_route', filter='User.username=="%s"' % test_user.username),
        {'draw': 1, 'start': 0, 'length': 1})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['username'] == test_user.username


def test_user_add_route(cl_admin):
    """user add route test"""

    tmp_password = PWS().generate()
    test_user = create_test_user()

    form = cl_admin.get(url_for('auth.user_add_route')).form
    form['username'] = test_user.username
    form['password'] = tmp_password
    form['roles'] = test_user.roles
    form['active'] = test_user.active
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == test_user.username).one()
    assert user.username == test_user.username
    assert PWS.compare(PWS.hash(tmp_password, PWS.get_salt(user.password)), user.password)
    assert user.active == test_user.active
    assert user.roles == test_user.roles


def test_user_edit_route(cl_admin, test_user):
    """user edit route test"""

    form = cl_admin.get(url_for('auth.user_edit_route', user_id=test_user.id)).form
    form['username'] = form['username'].value + '_edited'
    form['roles'] = []
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == form['username'].value).one()
    assert user.username == form['username'].value
    assert not user.roles


def test_user_delete_route(cl_admin, test_user):
    """user delete route test"""

    form = cl_admin.get(url_for('auth.user_delete_route', user_id=test_user.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not User.query.filter(User.username == test_user.username).one_or_none()


def test_user_apikey_route(cl_admin, test_user):
    """user apikey route test"""

    data = {'csrf_token': get_csrf_token(cl_admin)}

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=test_user.id, action='generate'), data)
    assert response.status_code == HTTPStatus.OK
    assert User.query.get(test_user.id).apikey

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=test_user.id, action='revoke'), data)
    assert response.status_code == HTTPStatus.OK
    assert not User.query.get(test_user.id).apikey

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=test_user.id, action='invalid'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
