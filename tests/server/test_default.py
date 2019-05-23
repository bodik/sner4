"""server functions tests"""

import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

from sner.server import cli, get_dotted


def test_get_dotted_function():
    """test dotted access to the nested dictionary helper"""

    data = {'a': {'b': 1}}
    assert get_dotted(data, 'a') == {'b': 1}
    assert get_dotted(data, 'a.b') == 1
    assert get_dotted(data, 'a.b.c') is None


def test_datetime_filter(app):
    """test datetime jinja filter"""

    assert app.jinja_env.filters['datetime'](datetime.fromisoformat('2000-01-01T00:00:00')) == '2000-01-01T00:00:00'
    assert app.jinja_env.filters['datetime'](None) == ''


def test_cli():
    """test sner server cli/main flask wrapper"""

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        with patch.object(sys, 'argv', []):
            with patch.object(os, 'environ', {}):
                cli()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
