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


def test_user_list_route(cl_admin):
    """user list route test"""

    response = cl_admin.get(url_for('auth.user_list_route'))
    assert response.status_code == HTTPStatus.OK


def test_user_list_json_route(cl_admin, user):
    """user list_json route test"""

    response = cl_admin.post(url_for('auth.user_list_json_route'), {'draw': 1, 'start': 0, 'length': 1, 'search[value]': user.username})
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['username'] == user.username

    response = cl_admin.post(
        url_for('auth.user_list_json_route', filter=f'User.username=="{user.username}"'),
        {'draw': 1, 'start': 0, 'length': 1}
    )
    assert response.status_code == HTTPStatus.OK
    response_data = json.loads(response.body.decode('utf-8'))
    assert response_data['data'][0]['username'] == user.username


def test_user_add_route(cl_admin, user_factory):
    """user add route test"""

    password = PWS.generate()
    auser = user_factory.build()

    form = cl_admin.get(url_for('auth.user_add_route')).form
    form['username'] = auser.username
    form['roles'] = auser.roles
    form['active'] = auser.active
    form['new_password'] = password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tuser = User.query.filter(User.username == auser.username).one()
    assert tuser.username == auser.username
    assert PWS.compare(PWS.hash(password, PWS.get_salt(tuser.password)), tuser.password)
    assert tuser.active == auser.active
    assert tuser.roles == auser.roles


def test_user_edit_route(cl_admin, user):
    """user edit route test"""

    password = PWS.generate()

    form = cl_admin.get(url_for('auth.user_edit_route', user_id=user.id)).form
    form['username'] = f'{form["username"].value}_edited'
    form['new_password'] = password
    form['roles'] = []
    form['api_networks'] = '127.0.0.0/23\n192.0.2.0/24\n2001:db8::/48'
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    tuser = User.query.filter(User.username == form['username'].value).one()
    assert tuser.username == form['username'].value
    assert PWS.compare(PWS.hash(password, PWS.get_salt(tuser.password)), tuser.password)
    assert not user.roles
    assert user.api_networks == ['127.0.0.0/23', '192.0.2.0/24', '2001:db8::/48']

    form = cl_admin.get(url_for('auth.user_edit_route', user_id=user.id)).form
    form['api_networks'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//div[@class="invalid-feedback" and contains(text(), "does not appear to be an IPv4 or IPv6 network")]')


def test_user_delete_route(cl_admin, user):
    """user delete route test"""

    form = cl_admin.get(url_for('auth.user_delete_route', user_id=user.id)).form
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    assert not User.query.filter(User.username == user.username).one_or_none()


def test_user_apikey_route(cl_admin, user):
    """user apikey route test"""

    data = {'csrf_token': get_csrf_token(cl_admin)}

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=user.id, action='generate'), data)
    assert response.status_code == HTTPStatus.OK
    assert User.query.get(user.id).apikey

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=user.id, action='revoke'), data)
    assert response.status_code == HTTPStatus.OK
    assert not User.query.get(user.id).apikey

    response = cl_admin.post(url_for('auth.user_apikey_route', user_id=user.id, action='invalid'), status='*')
    assert response.status_code == HTTPStatus.BAD_REQUEST
