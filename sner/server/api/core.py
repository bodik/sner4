# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api functions
"""

from sqlalchemy import func

from sner.server.extensions import db
from sner.server.scheduler.models import Job, Queue, Target
from sner.server.storage.models import Host, Note, Service, Vuln


def get_internal_stats():
    """returns dict of various internal stats"""

    queues = dict(
        db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    )

    result = {
        'scheduler': {
            'queues': queues,
            'jobs': {
                'running': Job.query.filter(Job.retval == None).count(),  # noqa: E501,E711  pylint: disable=singleton-comparison
                'finished': Job.query.filter(Job.retval == 0).count(),
                'failed': Job.query.filter(Job.retval != 0).count()
            }
        },
        'storage': {
            'hosts': Host.query.count(),
            'services': Service.query.count(),
            'vulns': Vuln.query.count(),
            'notes': Note.query.count()
        }
    }

    return result
