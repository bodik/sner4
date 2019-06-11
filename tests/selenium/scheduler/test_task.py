"""selenium ui tests for scheduler.task component"""

from flask import url_for

from sner.server.model.scheduler import Task
from tests.selenium import dt_inrow_delete, dt_rendered


def test_task_list_route(live_server, sl_operator, test_task):  # pylint: disable=unused-argument
    """simple test ajaxed datatable rendering"""

    sl_operator.get(url_for('scheduler.task_list_route', _external=True))
    dt_rendered(sl_operator, 'task_list_table', test_task.name)


def test_task_list_route_inrow_delete(live_server, sl_operator, test_task):  # pylint: disable=unused-argument
    """delete task inrow button"""

    sl_operator.get(url_for('scheduler.task_list_route', _external=True))
    dt_inrow_delete(sl_operator, 'task_list_table')
    assert not Task.query.filter(Task.id == test_task.id).one_or_none()
