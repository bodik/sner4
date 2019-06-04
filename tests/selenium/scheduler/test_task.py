"""selenium ui tests for scheduler.task component"""

from flask import url_for

from sner.server.model.scheduler import Task
from tests.selenium import dt_inrow_delete, dt_rendered


def test_list(live_server, selenium, test_task):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    selenium.get(url_for('scheduler.task_list_route', _external=True))
    dt_rendered(selenium, 'task_list_table', test_task.name)


def test_list_inrow_delete(live_server, selenium, test_task):  # pylint: disable=unused-argument
    """delete task inrow button"""

    selenium.get(url_for('scheduler.task_list_route', _external=True))
    dt_inrow_delete(selenium, 'task_list_table')
    assert not Task.query.filter(Task.id == test_task.id).one_or_none()
