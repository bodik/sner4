# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
test planner steps unittests
"""

from pathlib import Path

import pytest
from flask import current_app

from sner.server.parser import ParsedHost, ParsedService
from sner.server.planner.core import Context
from sner.server.planner.steps import (
    archive_job,
    enqueue,
    enumerate_ipv4,
    filter_netranges,
    filter_tarpits,
    import_job,
    load_job,
    project_hostlist,
    project_servicelist,
    rescan_hosts,
    rescan_services,
    run_group,
    stop_pipeline,
    StopPipeline,
    storage_cleanup,
    storage_ipv6_enum
)
from sner.server.scheduler.models import Job, Target
from sner.server.storage.models import Host, Service
from sner.server.utils import yaml_dump


def test_stop_pipeline():
    """test step"""

    with pytest.raises(StopPipeline):
        stop_pipeline({})


def test_load_import_archive(app, queue_factory, job_completed_factory):  # pylint: disable=unused-argument
    """test load, import, archive steps"""

    queue = queue_factory.create(
        name='test queue',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )
    job_completed_factory.create(
        queue=queue,
        make_output=Path('tests/server/data/parser-nmap-job.zip').read_bytes()
    )
    ctx = Context()

    ctx = load_job(ctx, queue.name)
    assert ctx.job
    assert len(ctx.data['hosts']) == 1
    assert len(ctx.data['services']) == 5

    ctx = import_job(ctx)
    assert len(Host.query.all()) == 1
    assert len(Service.query.all()) == 5

    ctx = archive_job(ctx)
    archive_path = Path(current_app.config['SNER_VAR']) / 'planner_archive' / f'{ctx.job.id}'
    assert archive_path.exists()

    # trigger stop pipeline when no job finished
    with pytest.raises(StopPipeline):
        ctx = load_job(ctx, queue.name)


def test_project_servicelist():
    """test project servicelist"""

    ctx = Context(data={
        'services': [
            ParsedService(handle={'host': '127.0.2.1', 'service': 'tcp/1'}, proto='tcp', port='1'),
            ParsedService(handle={'host': '::1', 'service': 'tcp/1'}, proto='tcp', port='1')
        ]
    })

    ctx = project_servicelist(ctx)

    expected = ['tcp://127.0.2.1:1', 'tcp://[::1]:1']
    assert ctx.data == expected


def test_project_hostlist():
    """test project hostlist"""

    ctx = Context(data={
        'hosts': [
            ParsedHost(handle={'host': '127.0.2.1'}, address='127.0.2.1'),
            ParsedHost(handle={'host': '::1'}, address='::1')
        ]
    })

    ctx = project_hostlist(ctx)

    expected = ['127.0.2.1', '::1']
    assert ctx.data == expected


def test_filter_tarpits(app):  # pylint: disable=unused-argument
    """test filter tarpits"""

    ctx = Context(
        job=Job(id='atestjobid'),
        data={'services': [ParsedService(handle={'host': '127.0.3.1', 'service': 'tcp/1'}, proto='tcp', port='1')]}
    )
    for port in range(201):
        ctx.data['services'].append(ParsedService(handle={'host': '127.0.4.1', 'service': f'tcp/{port}'}, proto='tcp', port=f'{port}'))

    ctx = filter_tarpits(ctx)

    assert len(ctx.data['services']) == 1


def test_filter_netranges():
    """test filter netranges"""

    ctx = Context(data=['127.0.0.1', '127.0.1.1'])

    ctx = filter_netranges(ctx, ['::/0', '127.0.0.0/24'])

    assert ctx.data == ['127.0.0.1']


def test_enqueue(app, queue):  # pylint: disable=unused-argument
    """test enqueue"""

    ctx = Context(data=['target1'])

    ctx = enqueue(ctx, queue.name)

    assert Target.query.count() == 1


def test_run_group(app):  # pylint: disable=unused-argument
    """test run steps by group definition"""

    current_app.config['SNER_PLANNER']['step_groups'] = {
        'a_test_group': [
            {'step': 'project_servicelist'}
        ]
    }

    ctx = Context(
        job=Job(id='atestjobid'),
        data={'services': [ParsedService(handle={'host': '127.0.3.1', 'service': 'tcp/1'}, proto='tcp', port='1')]}
    )

    ctx = run_group(ctx, 'a_test_group')

    assert ctx.data == ['tcp://127.0.3.1:1']


def test_enumerate_ipv4(app):  # pylint: disable=unused-argument
    """test enumerate_ipv4"""

    ctx = enumerate_ipv4(Context(), netranges=['127.0.0.0/24'])

    assert len(ctx.data) == 256


def test_rescan_services(app, host_factory, service_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_services pipeline"""

    service_factory.create(host=host_factory.create(address='127.0.0.1'))
    service_factory.create(host=host_factory.create(address='::1'))
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )

    ctx = rescan_services(Context(), '0s')

    assert len(ctx.data) == 2


def test_rescan_hosts(app, host_factory, queue_factory):  # pylint: disable=unused-argument
    """test rescan_hosts"""

    host_factory.create(address='127.0.0.1')
    host_factory.create(address='::1')
    queue_factory.create(
        name='test vscan',
        config=yaml_dump({'module': 'nmap', 'args': 'arg1'}),
    )

    ctx = rescan_hosts(Context(), '0s')

    assert len(ctx.data) == 2


def test_storage_ipv6_enum(app, queue, host_factory):  # pylint: disable=unused-argument
    """test storage ipv6 enum generator"""

    host_factory.create(address='::1')
    host_factory.create(address='::00ff:fe00:1')

    ctx = storage_ipv6_enum(Context())

    assert len(ctx.data) == 1


def test_storage_cleanup(app, host_factory, service_factory, note_factory):  # pylint: disable=unused-argument
    """test planners cleanup storage stage"""

    host_factory.create(address='127.127.127.134', hostname=None, os=None, comment=None)
    host1 = host_factory.create(address='127.127.127.135', os='identified')
    service_factory.create(host=host1, proto='tcp', port=1, state='open:reason')
    service_factory.create(host=host1, proto='tcp', port=1, state='filtered:reason')
    host2 = host_factory.create(address='127.127.127.136', hostname=None, os=None, comment=None)
    note_factory.create(host=host2, xtype='hostnames', data='adata')

    storage_cleanup(Context())

    assert Host.query.count() == 1
    assert Service.query.count() == 1
