"""controller auth.user tests"""

import json
from http import HTTPStatus

from flask import url_for

from sner.server.model.auth import User
from sner.server.password_supervisor import PasswordSupervisor
from tests.server.model.auth import create_test_user


def test_user_list_route(cl_admin):
    """user list route test"""

    response = cl_admin.get(url_for('auth.user_list_route'))
    assert response.status_code == HTTPStatus.OK
    assert '<h1>Users list' in response


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

    tmp_password = PasswordSupervisor().generate()
    test_user = create_test_user()

    form = cl_admin.get(url_for('auth.user_add_route')).form
    form['username'] = test_user.username
    form['password'] = tmp_password
    form['roles'] = test_user.roles
    form['active'] = test_user.active
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == test_user.username).one_or_none()
    assert user
    assert user.username == test_user.username
    assert user.compare_password(tmp_password)
    assert user.active == test_user.active
    assert user.roles == test_user.roles


def test_user_edit_route(cl_admin, test_user):
    """user edit route test"""

    form = cl_admin.get(url_for('auth.user_edit_route', user_id=test_user.id)).form
    form['username'] = form['username'].value + '_edited'
    form['roles'] = []
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == form['username'].value).one_or_none()
    assert user
    assert user.username == form['username'].value
    assert not user.roles


def test_user_delete_route(cl_admin, test_user):
    """user delete route test"""

    form = cl_admin.get(url_for('auth.user_delete_route', user_id=test_user.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == test_user.username).one_or_none()
    assert not user


def test_user_changepassword_route(cl_user):
    """user change password route"""

    tmp_password = PasswordSupervisor().generate()

    form = cl_user.get(url_for('auth.user_changepassword_route')).form
    form['password1'] = '1'
    form['password2'] = '2'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//*[@class="text-danger" and text()="Passwords does not match."]')

    form = cl_user.get(url_for('auth.user_changepassword_route')).form
    form['password1'] = 'weak'
    form['password2'] = 'weak'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//*[@class="text-danger" and contains(text(), "Password too short.")]')

    form = cl_user.get(url_for('auth.user_changepassword_route')).form
    form['password1'] = tmp_password
    form['password2'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    user = User.query.filter(User.username == 'pytest_user').one_or_none()
    assert user.compare_password(tmp_password)
