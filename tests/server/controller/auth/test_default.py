"""auth controler tests"""

from http import HTTPStatus

from flask import url_for

from sner.server import db
from sner.server.model.auth import User
from sner.server.password_supervisor import PasswordSupervisor as PWS


def test_login(client, test_user):
    """test login"""

    tmp_password = PWS().generate()
    tmp = User.query.filter(User.id == test_user.id).one_or_none()
    tmp.password = tmp_password
    db.session.commit()

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    form['password'] = 'invalid'
    response = form.submit()
    assert response.status_code == HTTPStatus.OK
    assert response.lxml.xpath('//script[contains(text(), "toastr[\'error\'](\'Invalid credentials\');")]')

    form = client.get(url_for('auth.login_route')).form
    form['username'] = test_user.username
    form['password'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND

    response = client.get(url_for('index_route'))
    assert response.lxml.xpath('//a[text()="Logout"]')


def test_logout(cl_user):
    """test logout"""

    response = cl_user.get(url_for('auth.logout_route'))
    assert response.status_code == HTTPStatus.FOUND
    response = response.follow()
    assert response.lxml.xpath('//a[text()="Login"]')


def test_unauthorized(client, test_user):
    """test for not logged in, redirect and final login"""

    tmp_password = PWS().generate()
    tmp = User.query.filter(User.id == test_user.id).one_or_none()
    tmp.password = tmp_password
    db.session.commit()

    response = client.get(url_for('auth.user_changepassword_route'))
    assert response.status_code == HTTPStatus.FOUND
    assert '/auth/login?next=' in response.headers['Location']

    form = response.follow().form
    form['username'] = test_user.username
    form['password'] = tmp_password
    response = form.submit()
    assert response.status_code == HTTPStatus.FOUND
    assert url_for('auth.user_changepassword_route') in response.headers['Location']


def test_forbidden(cl_user):
    """access forbidden"""

    response = cl_user.get(url_for('auth.user_list_route'), status='*')
    assert response.status_code == HTTPStatus.FORBIDDEN
