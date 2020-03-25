# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
server functions tests
"""

import os
import sys
from datetime import datetime
from http import HTTPStatus
from io import StringIO
from unittest.mock import patch

import pytest
from flask import url_for

from sner.lib import get_dotted
from sner.server.app import cli
from sner.version import __version__


def test_get_dotted_function():
    """test dotted access to the nested dictionary helper"""

    data = {'a': {'b': 1}}
    assert get_dotted(data, 'a') == {'b': 1}
    assert get_dotted(data, 'a.b') == 1
    assert get_dotted(data, 'a.b.c') is None


def test_datetime_filter(app):
    """test datetime jinja filter"""

    assert app.jinja_env.filters['datetime'](datetime.strptime('2000-01-01T00:00:00', '%Y-%m-%dT%H:%M:%S')) == '2000-01-01T00:00:00'
    assert app.jinja_env.filters['datetime'](None) == ''


def test_json_indent_filter(app):
    """test indenting filter"""

    assert app.jinja_env.filters['json_indent']('"xxx"') == '"xxx"'
    assert app.jinja_env.filters['json_indent']('xxx') == 'xxx'


def test_shell():
    """test shell context imports"""

    buf_stdin = StringIO('print(db.session)\n')
    buf_stdout = StringIO()

    patch_argv = patch.object(sys, 'argv', ['bin/server', 'shell'])
    patch_environ = patch.object(os, 'environ', {})
    patch_stdin = patch.object(sys, 'stdin', buf_stdin)
    patch_stdout = patch.object(sys, 'stdout', buf_stdout)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with patch_argv, patch_environ, patch_stdin, patch_stdout:
            cli()

    assert pytest_wrapped_e.value.code == 0
    assert 'sqlalchemy.orm.scoping.scoped_session' in buf_stdout.getvalue()


def test_index_route(client):
    """test root url"""

    response = client.get(url_for('index_route'))
    assert response.status_code == HTTPStatus.OK
    assert 'logo.png' in response


def test_cli():
    """test sner server cli/main flask wrapper"""

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with patch.object(sys, 'argv', []):
            with patch.object(os, 'environ', {}):
                cli()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_version():
    """test sner server cli/main flask wrapper"""

    buf_stdout = StringIO()

    patch_argv = patch.object(sys, 'argv', ['--version'])
    patch_environ = patch.object(os, 'environ', {})
    patch_stdout = patch.object(sys, 'stdout', buf_stdout)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with patch_argv, patch_environ, patch_stdout:
            cli()

    assert pytest_wrapped_e.value.code == 0
    assert 'Sner %s' % __version__ in buf_stdout.getvalue()
