# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
"""
api functions
"""

from datetime import datetime, timedelta

from sqlalchemy import func

from sner.server.extensions import db

from sner.server.scheduler.models import Heatmap, Job, Queue, Readynet, Target
from sner.server.storage.models import Host, Note, Service, Vuln, VersionInfo


def get_metrics():
    """grab internal metrics"""

    metrics = {}

    metrics['sner_storage_hosts_total'] = Host.query.count()
    metrics['sner_storage_services_total'] = Service.query.count()
    metrics['sner_storage_vulns_total'] = Vuln.query.count()
    metrics['sner_storage_notes_total'] = Note.query.count()
    metrics['sner_storage_versioninfo_total'] = VersionInfo.query.count()

    queue_targets = db.session.query(Queue.name, func.count(Target.id).label('cnt')).select_from(Queue).outerjoin(Target).group_by(Queue.name).all()
    for queue, targets in queue_targets:
        metrics[f'sner_scheduler_queue_targets_total{{name="{queue}"}}'] = targets
    metrics['sner_scheduler_targets_total'] = Target.query.count()

    stale_horizont = datetime.utcnow() - timedelta(days=5)
    metrics['sner_scheduler_jobs_total{state="running"}'] = Job.query.filter(Job.retval == None, Job.time_start > stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    metrics['sner_scheduler_jobs_total{state="stale"}'] = Job.query.filter(Job.retval == None, Job.time_start < stale_horizont).count()  # noqa: E501,E711  pylint: disable=singleton-comparison
    metrics['sner_scheduler_jobs_total{state="finished"}'] = Job.query.filter(Job.retval == 0).count()
    metrics['sner_scheduler_jobs_total{state="failed"}'] = Job.query.filter(Job.retval != 0).count()

    metrics['sner_scheduler_heatmap_hashvals_total'] = Heatmap.query.count()
    metrics['sner_scheduler_heatmap_targets_total'] = db.session.query(func.sum(Heatmap.count)).scalar()

    metrics['sner_scheduler_readynets_available_total'] = db.session.query(func.distinct(Readynet.hashval)).count()

    output = '\n'.join(f'{key} {val}' for key, val in metrics.items())
    return output
